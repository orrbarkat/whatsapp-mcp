"""Database abstraction layer using Protocol-based repository interfaces.

This module defines Protocol interfaces for data access operations, enabling
dependency injection and supporting multiple backend implementations (SQLite, Supabase, etc.)
without changing business logic.

The repository pattern separates data access concerns from business logic,
making the codebase more testable and maintainable.
"""

from typing import Protocol, Optional, List, Tuple, Any
from models import Message, Chat, Contact, MessageContext


class MessageRepository(Protocol):
    """Protocol for message data access operations.

    Implementations must provide methods to query and retrieve messages
    from the data store. All methods return domain entities, not formatted strings.
    """

    def get_sender_name(self, sender_jid: str) -> str:
        """Resolve a sender JID to a display name.

        Args:
            sender_jid: The JID (or phone number) of the sender to look up

        Returns:
            The display name if found, otherwise the original sender_jid
        """
        ...

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
        ...

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
        ...


class ChatRepository(Protocol):
    """Protocol for chat data access operations.

    Implementations must provide methods to query and retrieve chat metadata.
    """

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
        ...

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
        ...

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
        ...


class ContactRepository(Protocol):
    """Protocol for contact data access operations.

    Implementations must provide methods to search and retrieve contact information.
    """

    def search_contacts(self, query: str) -> List[Contact]:
        """Search for contacts by name or phone number.

        Args:
            query: Search query (matches name or JID, case-insensitive)

        Returns:
            List of Contact objects matching the query (up to 50 results)
        """
        ...

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
        ...

    def get_last_interaction(self, jid: str) -> Optional[Message]:
        """Retrieve the most recent message involving a contact.

        Args:
            jid: The JID of the contact

        Returns:
            The most recent Message from or to the contact, or None if no messages exist
        """
        ...


class AuthenticationRepository(Protocol):
    """Protocol for authentication status operations.

    Implementations must provide methods to check WhatsApp authentication state.
    """

    def check_authentication_status(self) -> Tuple[bool, Optional[str]]:
        """Check if WhatsApp is authenticated.

        Returns:
            Tuple of (is_authenticated, error_message).
            If authenticated, error_message is None.
            If not authenticated, error_message describes why.
        """
        ...


class DatabaseConnection(Protocol):
    """Protocol for low-level database connection management.

    Implementations must provide connection lifecycle and basic execution methods.
    This protocol is backend-agnostic and supports various database implementations.
    """

    def connect(self) -> None:
        """Establish a connection to the database.

        This method initializes the connection to the underlying database.
        Should be called before any database operations are performed.

        Raises:
            ConnectionError: If the connection cannot be established
        """
        ...

    def cursor(self) -> Any:
        """Create and return a database cursor for executing queries.

        Returns:
            A cursor object that can be used to execute queries and fetch results.
            The exact type depends on the backend implementation.
        """
        ...

    def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a SQL query with optional parameters.

        Args:
            query: SQL query string to execute
            params: Optional tuple of parameters for parameterized queries

        Returns:
            Result of the query execution (backend-specific)

        Raises:
            DatabaseError: If the query execution fails
        """
        ...

    def fetchone(self) -> Optional[Tuple]:
        """Fetch the next row from the last executed query.

        Returns:
            A tuple representing the next row, or None if no more rows are available
        """
        ...

    def fetchall(self) -> List[Tuple]:
        """Fetch all remaining rows from the last executed query.

        Returns:
            List of tuples, where each tuple represents a row from the result set
        """
        ...

    def commit(self) -> None:
        """Commit the current transaction.

        Persists all changes made in the current transaction to the database.
        """
        ...

    def rollback(self) -> None:
        """Roll back the current transaction.

        Discards all changes made in the current transaction.
        """
        ...

    def close(self) -> None:
        """Close the database connection and release resources.

        Should be called when the connection is no longer needed.
        This ensures proper cleanup of database resources.
        """
        ...


class UnitOfWork(Protocol):
    """Protocol for transaction management across repository operations.

    Provides transactional boundaries to ensure data consistency when
    multiple repository operations must succeed or fail together.

    Usage:
        with adapter.unit_of_work() as uow:
            # Perform multiple repository operations
            messages_repo.create_message(...)
            chats_repo.update_last_message(...)
            # Explicitly commit if all operations succeed
            uow.commit()
        # If an exception occurs, rollback is automatic

    The UnitOfWork follows the context manager pattern. If an exception
    occurs within the context, rollback() is called automatically. Otherwise,
    changes must be explicitly committed by calling commit().
    """

    def begin(self) -> None:
        """Begin a new transaction.

        This is typically called automatically when entering the context manager.
        """
        ...

    def commit(self) -> None:
        """Commit the current transaction.

        All changes made within the transaction are persisted to the database.
        Must be called explicitly before exiting the context manager to save changes.
        """
        ...

    def rollback(self) -> None:
        """Roll back the current transaction.

        All changes made within the transaction are discarded.
        This is called automatically if an exception occurs in the context manager.
        """
        ...

    def __enter__(self) -> "UnitOfWork":
        """Enter the transaction context.

        Returns:
            Self, to allow usage in with statements
        """
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the transaction context.

        If an exception occurred (exc_type is not None), rollback is performed.
        Otherwise, no automatic action is taken (commit must be explicit).

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        ...


class DatabaseAdapter(Protocol):
    """Composite protocol providing access to all repository interfaces.

    This is the main entry point for data access operations. Implementations
    must provide access to all repository interfaces and lifecycle management.

    The adapter pattern allows swapping entire database backends (SQLite, Supabase)
    without changing business logic.
    """

    @property
    def messages(self) -> MessageRepository:
        """Access the message repository.

        Returns:
            MessageRepository implementation
        """
        ...

    @property
    def chats(self) -> ChatRepository:
        """Access the chat repository.

        Returns:
            ChatRepository implementation
        """
        ...

    @property
    def contacts(self) -> ContactRepository:
        """Access the contact repository.

        Returns:
            ContactRepository implementation
        """
        ...

    @property
    def authentication(self) -> AuthenticationRepository:
        """Access the authentication repository.

        Returns:
            AuthenticationRepository implementation
        """
        ...

    def unit_of_work(self) -> UnitOfWork:
        """Create a new unit of work for transactional operations.

        Returns:
            UnitOfWork instance for managing transactions

        Usage:
            with adapter.unit_of_work() as uow:
                # Perform operations
                uow.commit()
        """
        ...

    def close(self) -> None:
        """Close all connections and release resources.

        Should be called when the adapter is no longer needed.
        """
        ...
