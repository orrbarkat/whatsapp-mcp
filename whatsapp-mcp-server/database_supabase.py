"""Supabase implementation of the database abstraction layer.

This module provides concrete implementations of the repository protocols
defined in database.py, using Supabase as the backend storage.

The implementation uses the Supabase Python client to interact with a PostgreSQL
database via PostgREST API, avoiding direct SQL joins by using embedded selects
and foreign key relationships.
"""

import os
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from supabase import create_client, Client

from models import Message, Chat, Contact, MessageContext

logger = logging.getLogger(__name__)


class SupabaseMessageRepository:
    """Supabase implementation of MessageRepository.

    Provides methods to query and retrieve messages from Supabase.
    """

    def __init__(self, client: Client):
        """Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance for API calls
        """
        self.client = client

    def get_sender_name(self, sender_jid: str) -> str:
        """Resolve a sender JID to a display name.

        Args:
            sender_jid: The JID (or phone number) of the sender to look up

        Returns:
            The display name if found, otherwise the original sender_jid
        """
        try:
            # Try to find contact by JID
            response = self.client.table("whatsmeow_contacts").select("pushname, fullname").eq("our_jid", sender_jid).limit(1).execute()

            if response.data and len(response.data) > 0:
                contact = response.data[0]
                # Return fullname if available, otherwise pushname, otherwise JID
                return contact.get("fullname") or contact.get("pushname") or sender_jid

            return sender_jid
        except Exception as e:
            logger.error(f"Error resolving sender name for {sender_jid}: {e}")
            return sender_jid

    def list_messages(
        self,
        after: Optional[str] = None,
        before: Optional[str] = None,
        sender_phone_number: Optional[str] = None,
        chat_jid: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
        page: int = 0,
        include_context: bool = True,
        context_before: int = 1,
        context_after: int = 1
    ) -> List[Message]:
        """Retrieve messages matching the specified filters.

        Args:
            after: ISO-8601 timestamp; only return messages after this time
            before: ISO-8601 timestamp; only return messages before this time
            sender_phone_number: Filter by sender phone number/JID
            chat_jid: Filter by chat JID
            query: Text search query (case-insensitive substring match on content)
            limit: Maximum number of messages to return
            page: Page number for pagination (0-indexed)
            include_context: If True, include context messages around each result
            context_before: Number of context messages to include before each result
            context_after: Number of context messages to include after each result

        Returns:
            List of Message objects matching the criteria. If include_context is True,
            the list will include context messages interleaved with matched messages.

        Raises:
            ValueError: If date format is invalid
        """
        try:
            # Parse date filters if provided
            after_dt = None
            before_dt = None

            if after:
                try:
                    after_dt = datetime.fromisoformat(after.replace('Z', '+00:00'))
                except ValueError as e:
                    raise ValueError(f"Invalid 'after' date format: {after}") from e

            if before:
                try:
                    before_dt = datetime.fromisoformat(before.replace('Z', '+00:00'))
                except ValueError as e:
                    raise ValueError(f"Invalid 'before' date format: {before}") from e

            # Build query
            query_builder = self.client.table("whatsmeow_history_messages").select("*")

            # Apply filters
            if after_dt:
                query_builder = query_builder.gte("timestamp", after_dt.isoformat())

            if before_dt:
                query_builder = query_builder.lte("timestamp", before_dt.isoformat())

            if sender_phone_number:
                query_builder = query_builder.eq("sender", sender_phone_number)

            if chat_jid:
                query_builder = query_builder.eq("chat", chat_jid)

            if query:
                # Use ilike for case-insensitive substring search
                query_builder = query_builder.ilike("text", f"%{query}%")

            # Apply pagination
            offset = page * limit
            query_builder = query_builder.order("timestamp", desc=False).range(offset, offset + limit - 1)

            # Execute query
            response = query_builder.execute()

            if not response.data:
                return []

            # Convert to domain models
            messages = []
            for row in response.data:
                msg = self._row_to_message(row)
                messages.append(msg)

                # Add context if requested
                if include_context:
                    context_messages = self._get_context_messages(
                        row["id"],
                        row["chat"],
                        row["timestamp"],
                        context_before,
                        context_after
                    )
                    messages.extend(context_messages)

            return messages

        except ValueError:
            # Re-raise ValueError for date parsing errors
            raise
        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return []

    def get_message_context(
        self,
        message_id: str,
        before: int = 5,
        after: int = 5
    ) -> MessageContext:
        """Retrieve a message with surrounding context.

        Args:
            message_id: Unique identifier of the target message
            before: Number of messages to include before the target
            after: Number of messages to include after the target

        Returns:
            MessageContext containing the target message and surrounding messages

        Raises:
            ValueError: If message_id is not found
        """
        try:
            # Get the target message
            response = self.client.table("whatsmeow_history_messages").select("*").eq("id", message_id).limit(1).execute()

            if not response.data or len(response.data) == 0:
                raise ValueError(f"Message with id {message_id} not found")

            target_row = response.data[0]
            target_message = self._row_to_message(target_row)

            # Get messages before
            before_response = self.client.table("whatsmeow_history_messages").select("*").eq("chat", target_row["chat"]).lt("timestamp", target_row["timestamp"]).order("timestamp", desc=True).limit(before).execute()

            before_messages = [self._row_to_message(row) for row in reversed(before_response.data)] if before_response.data else []

            # Get messages after
            after_response = self.client.table("whatsmeow_history_messages").select("*").eq("chat", target_row["chat"]).gt("timestamp", target_row["timestamp"]).order("timestamp", desc=False).limit(after).execute()

            after_messages = [self._row_to_message(row) for row in after_response.data] if after_response.data else []

            return MessageContext(
                message=target_message,
                before=before_messages,
                after=after_messages
            )

        except ValueError:
            # Re-raise ValueError for not found
            raise
        except Exception as e:
            logger.error(f"Error getting message context for {message_id}: {e}")
            raise ValueError(f"Failed to retrieve message context: {e}")

    def _row_to_message(self, row: dict) -> Message:
        """Convert a database row to a Message domain model.

        Args:
            row: Dictionary representing a message row from Supabase

        Returns:
            Message domain model
        """
        # Parse timestamp
        timestamp = datetime.fromisoformat(row["timestamp"].replace('Z', '+00:00'))

        return Message(
            id=row["id"],
            timestamp=timestamp,
            sender=row.get("sender", ""),
            content=row.get("text", ""),
            is_from_me=row.get("from_me", False),
            chat_jid=row["chat"],
            chat_name=None,  # Will be populated by caller if needed
            media_type=row.get("media_type")
        )

    def _get_context_messages(
        self,
        message_id: str,
        chat_jid: str,
        timestamp: str,
        before: int,
        after: int
    ) -> List[Message]:
        """Get context messages around a specific message.

        Args:
            message_id: ID of the target message
            chat_jid: Chat JID the message belongs to
            timestamp: Timestamp of the target message
            before: Number of messages before to retrieve
            after: Number of messages after to retrieve

        Returns:
            List of Message objects (context messages only, not including target)
        """
        try:
            context_messages = []

            # Get messages before
            if before > 0:
                before_response = self.client.table("whatsmeow_history_messages").select("*").eq("chat", chat_jid).lt("timestamp", timestamp).order("timestamp", desc=True).limit(before).execute()

                if before_response.data:
                    context_messages.extend([self._row_to_message(row) for row in reversed(before_response.data)])

            # Get messages after
            if after > 0:
                after_response = self.client.table("whatsmeow_history_messages").select("*").eq("chat", chat_jid).gt("timestamp", timestamp).order("timestamp", desc=False).limit(after).execute()

                if after_response.data:
                    context_messages.extend([self._row_to_message(row) for row in after_response.data])

            return context_messages

        except Exception as e:
            logger.error(f"Error getting context messages: {e}")
            return []


class SupabaseChatRepository:
    """Supabase implementation of ChatRepository.

    Provides methods to query and retrieve chat metadata.
    """

    def __init__(self, client: Client):
        """Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance for API calls
        """
        self.client = client

    def list_chats(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        page: int = 0,
        include_last_message: bool = True,
        sort_by: str = "last_active"
    ) -> List[Chat]:
        """Retrieve chats matching the specified criteria.

        Args:
            query: Text search query (matches chat name or JID)
            limit: Maximum number of chats to return
            page: Page number for pagination (0-indexed)
            include_last_message: If True, populate last_message fields
            sort_by: Sort order - "last_active" (by last_message_time DESC) or "name"

        Returns:
            List of Chat objects matching the criteria
        """
        try:
            # Build query using the chat_list view
            # The view joins whatsmeow_chats with whatsmeow_history_messages
            # to provide chat info with last message details
            query_builder = self.client.table("chat_list").select("*")

            # Apply text search filter if provided
            if query:
                # Search in both name and JID using OR condition
                query_builder = query_builder.or_(f"name.ilike.%{query}%,jid.ilike.%{query}%")

            # Apply sorting
            if sort_by == "name":
                query_builder = query_builder.order("name", desc=False)
            else:  # last_active
                query_builder = query_builder.order("last_message_time", desc=True)

            # Apply pagination
            offset = page * limit
            query_builder = query_builder.range(offset, offset + limit - 1)

            # Execute query
            response = query_builder.execute()

            if not response.data:
                return []

            # Convert to domain models
            chats = []
            for row in response.data:
                chat = self._row_to_chat(row, include_last_message)
                chats.append(chat)

            return chats

        except Exception as e:
            logger.error(f"Error listing chats: {e}")
            return []

    def get_chat(
        self,
        chat_jid: str,
        include_last_message: bool = True
    ) -> Optional[Chat]:
        """Retrieve a single chat by JID.

        Args:
            chat_jid: The JID of the chat to retrieve
            include_last_message: If True, populate last_message fields

        Returns:
            Chat object if found, None otherwise
        """
        try:
            # Use RPC function to get chat with aggregated data
            response = self.client.rpc("get_chat_by_jid", {"p_chat_jid": chat_jid}).execute()

            if not response.data or len(response.data) == 0:
                return None

            return self._row_to_chat(response.data[0], include_last_message)

        except Exception as e:
            logger.error(f"Error getting chat {chat_jid}: {e}")
            return None

    def get_direct_chat_by_contact(
        self,
        sender_phone_number: str
    ) -> Optional[Chat]:
        """Retrieve a direct (non-group) chat by contact phone number.

        Args:
            sender_phone_number: Phone number or JID of the contact

        Returns:
            Chat object if a direct chat with this contact exists, None otherwise
        """
        try:
            # Use RPC function to find direct chat
            response = self.client.rpc("get_direct_chat_by_contact", {"p_contact_jid": sender_phone_number}).execute()

            if not response.data or len(response.data) == 0:
                return None

            return self._row_to_chat(response.data[0], include_last_message=True)

        except Exception as e:
            logger.error(f"Error getting direct chat for {sender_phone_number}: {e}")
            return None

    def _row_to_chat(self, row: dict, include_last_message: bool) -> Chat:
        """Convert a database row to a Chat domain model.

        Args:
            row: Dictionary representing a chat row from Supabase
            include_last_message: Whether to include last message fields

        Returns:
            Chat domain model
        """
        # Parse last_message_time if present
        last_message_time = None
        if row.get("last_message_time"):
            try:
                last_message_time = datetime.fromisoformat(row["last_message_time"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        return Chat(
            jid=row["jid"],
            name=row.get("name"),
            last_message_time=last_message_time,
            last_message=row.get("last_message") if include_last_message else None,
            last_sender=row.get("last_sender") if include_last_message else None,
            last_is_from_me=row.get("last_is_from_me") if include_last_message else None
        )


class SupabaseContactRepository:
    """Supabase implementation of ContactRepository.

    Provides methods to search and retrieve contact information.
    """

    def __init__(self, client: Client):
        """Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance for API calls
        """
        self.client = client

    def search_contacts(self, query: str) -> List[Contact]:
        """Search for contacts by name or phone number.

        Args:
            query: Search query (matches name or JID, case-insensitive)

        Returns:
            List of Contact objects matching the query (up to 50 results)
        """
        try:
            # Search in contacts table
            response = self.client.table("whatsmeow_contacts").select("*").or_(f"pushname.ilike.%{query}%,fullname.ilike.%{query}%,our_jid.ilike.%{query}%").limit(50).execute()

            if not response.data:
                return []

            # Convert to domain models
            contacts = []
            for row in response.data:
                contact = self._row_to_contact(row)
                contacts.append(contact)

            return contacts

        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return []

    def get_contact_chats(
        self,
        jid: str,
        limit: int = 20,
        page: int = 0
    ) -> List[Chat]:
        """Retrieve all chats involving a specific contact.

        This includes both direct chats and group chats where the contact
        has sent messages.

        Args:
            jid: The JID of the contact
            limit: Maximum number of chats to return
            page: Page number for pagination (0-indexed)

        Returns:
            List of Chat objects where the contact has participated
        """
        try:
            # Use RPC function to get chats for contact
            offset = page * limit
            response = self.client.rpc("get_contact_chats", {
                "p_contact_jid": jid,
                "p_limit": limit,
                "p_offset": offset
            }).execute()

            if not response.data:
                return []

            # Convert to domain models
            chats = []
            for row in response.data:
                chat = self._row_to_chat(row)
                chats.append(chat)

            return chats

        except Exception as e:
            logger.error(f"Error getting chats for contact {jid}: {e}")
            return []

    def get_last_interaction(self, jid: str) -> Optional[Message]:
        """Retrieve the most recent message involving a contact.

        Args:
            jid: The JID of the contact

        Returns:
            The most recent Message from or to the contact, or None if no messages exist
        """
        try:
            # Get most recent message from this sender
            response = self.client.table("whatsmeow_history_messages").select("*").eq("sender", jid).order("timestamp", desc=True).limit(1).execute()

            if not response.data or len(response.data) == 0:
                return None

            row = response.data[0]
            return self._row_to_message(row)

        except Exception as e:
            logger.error(f"Error getting last interaction for {jid}: {e}")
            return None

    def _row_to_contact(self, row: dict) -> Contact:
        """Convert a database row to a Contact domain model.

        Args:
            row: Dictionary representing a contact row from Supabase

        Returns:
            Contact domain model
        """
        jid = row["our_jid"]
        # Extract phone number from JID (remove @s.whatsapp.net suffix)
        phone_number = jid.split("@")[0] if "@" in jid else jid

        return Contact(
            jid=jid,
            phone_number=phone_number,
            name=row.get("fullname") or row.get("pushname")
        )

    def _row_to_chat(self, row: dict) -> Chat:
        """Convert a database row to a Chat domain model.

        Args:
            row: Dictionary representing a chat row from Supabase

        Returns:
            Chat domain model
        """
        # Parse last_message_time if present
        last_message_time = None
        if row.get("last_message_time"):
            try:
                last_message_time = datetime.fromisoformat(row["last_message_time"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        return Chat(
            jid=row["jid"],
            name=row.get("name"),
            last_message_time=last_message_time,
            last_message=row.get("last_message"),
            last_sender=row.get("last_sender"),
            last_is_from_me=row.get("last_is_from_me")
        )

    def _row_to_message(self, row: dict) -> Message:
        """Convert a database row to a Message domain model.

        Args:
            row: Dictionary representing a message row from Supabase

        Returns:
            Message domain model
        """
        # Parse timestamp
        timestamp = datetime.fromisoformat(row["timestamp"].replace('Z', '+00:00'))

        return Message(
            id=row["id"],
            timestamp=timestamp,
            sender=row.get("sender", ""),
            content=row.get("text", ""),
            is_from_me=row.get("from_me", False),
            chat_jid=row["chat"],
            chat_name=None,
            media_type=row.get("media_type")
        )


class SupabaseAuthenticationRepository:
    """Supabase implementation of AuthenticationRepository.

    Provides methods to check WhatsApp authentication state.
    """

    def __init__(self, client: Client):
        """Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance for API calls
        """
        self.client = client

    def check_authentication_status(self) -> Tuple[bool, Optional[str]]:
        """Check if WhatsApp is authenticated.

        Returns:
            Tuple of (is_authenticated, error_message).
            If authenticated, error_message is None.
            If not authenticated, error_message describes why.
        """
        try:
            # Check if whatsmeow_device table exists and has rows
            response = self.client.table("whatsmeow_device").select("*", count="exact").limit(1).execute()

            if response.data and len(response.data) > 0:
                return (True, None)
            else:
                return (False, "No device registered. Please scan QR code to authenticate.")

        except Exception as e:
            error_msg = str(e)

            # Check if table doesn't exist
            if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
                return (False, "WhatsApp device table not found. Database may not be initialized.")

            logger.error(f"Error checking authentication status: {e}")
            return (False, f"Failed to check authentication: {error_msg}")


class SupabaseUnitOfWork:
    """Supabase implementation of UnitOfWork.

    Note: Supabase PostgREST API does not support transactions in the traditional sense.
    This implementation provides the interface but with limited transactional guarantees.
    Each operation is atomic, but there's no rollback capability across multiple operations.
    """

    def __init__(self, client: Client):
        """Initialize the unit of work with a Supabase client.

        Args:
            client: Supabase client instance for API calls
        """
        self.client = client

    def begin(self) -> None:
        """Begin a new transaction.

        Note: This is a no-op for Supabase as transactions are not supported
        via the PostgREST API. Each operation is atomic by default.
        """
        # No-op: Supabase doesn't support explicit transactions via PostgREST
        pass

    def commit(self) -> None:
        """Commit the current transaction.

        Note: This is a no-op for Supabase as each operation is immediately
        committed to the database.
        """
        # No-op: Changes are automatically committed in Supabase
        pass

    def rollback(self) -> None:
        """Roll back the current transaction.

        Note: This is a no-op with a warning for Supabase. Rollback is not
        supported via the PostgREST API. Individual operations are atomic
        but cannot be rolled back once executed.
        """
        logger.warning("Rollback requested but not supported by Supabase PostgREST API. Each operation is atomic but cannot be rolled back.")
        # No-op: Supabase doesn't support rollback via PostgREST

    def __enter__(self) -> "SupabaseUnitOfWork":
        """Enter the transaction context.

        Returns:
            Self, to allow usage in with statements
        """
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the transaction context.

        If an exception occurred (exc_type is not None), rollback is attempted.
        Otherwise, no automatic action is taken (commit must be explicit).

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if exc_type is not None:
            self.rollback()
        # Note: commit() must be called explicitly, no automatic commit on success


class SupabaseDatabaseAdapter:
    """Supabase implementation of DatabaseAdapter.

    Provides a unified interface to all repository implementations and manages
    the Supabase client lifecycle. Uses a singleton client pattern to avoid
    creating multiple connections.
    """

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize the adapter with Supabase credentials.

        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase anon key (defaults to SUPABASE_ANON_KEY env var)

        Raises:
            ValueError: If credentials are not provided and not in environment
        """
        # Get credentials from parameters or environment
        self._url = supabase_url or os.getenv("SUPABASE_URL")
        self._key = supabase_key or os.getenv("SUPABASE_ANON_KEY")

        if not self._url or not self._key:
            raise ValueError("Supabase credentials not provided. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")

        # Create singleton Supabase client
        self._client = create_client(self._url, self._key)

        # Initialize repository instances
        self._messages = SupabaseMessageRepository(self._client)
        self._chats = SupabaseChatRepository(self._client)
        self._contacts = SupabaseContactRepository(self._client)
        self._authentication = SupabaseAuthenticationRepository(self._client)

    @property
    def messages(self) -> SupabaseMessageRepository:
        """Access the message repository.

        Returns:
            MessageRepository implementation
        """
        return self._messages

    @property
    def chats(self) -> SupabaseChatRepository:
        """Access the chat repository.

        Returns:
            ChatRepository implementation
        """
        return self._chats

    @property
    def contacts(self) -> SupabaseContactRepository:
        """Access the contact repository.

        Returns:
            ContactRepository implementation
        """
        return self._contacts

    @property
    def authentication(self) -> SupabaseAuthenticationRepository:
        """Access the authentication repository.

        Returns:
            AuthenticationRepository implementation
        """
        return self._authentication

    def unit_of_work(self) -> SupabaseUnitOfWork:
        """Create a new unit of work for transactional operations.

        Returns:
            UnitOfWork instance for managing transactions

        Usage:
            with adapter.unit_of_work() as uow:
                # Perform operations
                uow.commit()
        """
        return SupabaseUnitOfWork(self._client)

    def close(self) -> None:
        """Close all connections and release resources.

        Note: The Supabase Python client doesn't require explicit cleanup,
        but this method is provided for API consistency.
        """
        # Supabase client doesn't require explicit cleanup
        # This method is provided for API consistency
        logger.info("Supabase adapter closed")
