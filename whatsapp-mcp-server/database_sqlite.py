"""SQLite implementation of the database repository interfaces.

This module provides concrete SQLite implementations of all repository protocols
defined in database.py. It handles connection management, query execution, and
proper transaction handling.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Any
from contextlib import contextmanager
from models import Message, Chat, Contact, MessageContext


class SQLiteConnection:
    """Manages SQLite database connections with proper lifecycle handling."""

    def __init__(self, db_path: str):
        """Initialize connection manager.

        Args:
            db_path: Path to SQLite database file, or ':memory:' for in-memory database
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None

    def connect(self) -> None:
        """Establish a connection to the database."""
        if self.db_path == ':memory:':
            # Use shared cache for in-memory databases to allow multiple connections
            self._conn = sqlite3.connect('file::memory:?cache=shared', uri=True)
        else:
            self._conn = sqlite3.connect(self.db_path)

    def cursor(self) -> sqlite3.Cursor:
        """Create and return a database cursor."""
        if self._conn is None:
            self.connect()
        if self._cursor is None:
            self._cursor = self._conn.cursor()
        return self._cursor

    def execute(self, query: str, params: Optional[Tuple] = None) -> sqlite3.Cursor:
        """Execute a SQL query with optional parameters."""
        cursor = self.cursor()
        if params:
            return cursor.execute(query, params)
        return cursor.execute(query)

    def fetchone(self) -> Optional[Tuple]:
        """Fetch the next row from the last executed query."""
        if self._cursor is None:
            return None
        return self._cursor.fetchone()

    def fetchall(self) -> List[Tuple]:
        """Fetch all remaining rows from the last executed query."""
        if self._cursor is None:
            return []
        return self._cursor.fetchall()

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._conn:
            self._conn.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._conn:
            self._conn.rollback()

    def close(self) -> None:
        """Close the database connection and release resources."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn:
            self._conn.close()
            self._conn = None


class SQLiteUnitOfWork:
    """Manages transactions for SQLite operations."""

    def __init__(self, messages_conn: SQLiteConnection, auth_conn: SQLiteConnection):
        """Initialize unit of work with connections.

        Args:
            messages_conn: Connection to messages database
            auth_conn: Connection to authentication database
        """
        self.messages_conn = messages_conn
        self.auth_conn = auth_conn
        self._in_transaction = False

    def begin(self) -> None:
        """Begin a new transaction."""
        if not self._in_transaction:
            # SQLite starts transactions implicitly
            self._in_transaction = True

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._in_transaction:
            self.messages_conn.commit()
            self.auth_conn.commit()
            self._in_transaction = False

    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._in_transaction:
            self.messages_conn.rollback()
            self.auth_conn.rollback()
            self._in_transaction = False

    def __enter__(self) -> "SQLiteUnitOfWork":
        """Enter the transaction context."""
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the transaction context."""
        if exc_type is not None:
            self.rollback()
        # Note: Commit must be called explicitly


class SQLiteMessageRepository:
    """SQLite implementation of MessageRepository protocol."""

    def __init__(self, conn: SQLiteConnection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection to messages database
        """
        self.conn = conn

    def get_sender_name(self, sender_jid: str) -> str:
        """Resolve a sender JID to a display name."""
        try:
            # First try matching by exact JID
            self.conn.execute("""
                SELECT name
                FROM chats
                WHERE jid = ?
                LIMIT 1
            """, (sender_jid,))

            result = self.conn.fetchone()

            # If no result, try looking for the number within JIDs
            if not result:
                # Extract the phone number part if it's a JID
                if '@' in sender_jid:
                    phone_part = sender_jid.split('@')[0]
                else:
                    phone_part = sender_jid

                self.conn.execute("""
                    SELECT name
                    FROM chats
                    WHERE jid LIKE ?
                    LIMIT 1
                """, (f"%{phone_part}%",))

                result = self.conn.fetchone()

            if result and result[0]:
                return result[0]
            else:
                return sender_jid

        except sqlite3.Error as e:
            print(f"Database error while getting sender name: {e}")
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
        """Retrieve messages matching the specified filters."""
        try:
            # Build base query
            query_parts = ["SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type FROM messages"]
            query_parts.append("JOIN chats ON messages.chat_jid = chats.jid")
            where_clauses = []
            params = []

            # Add filters
            if after:
                try:
                    after_dt = datetime.fromisoformat(after)
                except ValueError:
                    raise ValueError(f"Invalid date format for 'after': {after}. Please use ISO-8601 format.")

                where_clauses.append("messages.timestamp > ?")
                params.append(after_dt)

            if before:
                try:
                    before_dt = datetime.fromisoformat(before)
                except ValueError:
                    raise ValueError(f"Invalid date format for 'before': {before}. Please use ISO-8601 format.")

                where_clauses.append("messages.timestamp < ?")
                params.append(before_dt)

            if sender_phone_number:
                where_clauses.append("messages.sender = ?")
                params.append(sender_phone_number)

            if chat_jid:
                where_clauses.append("messages.chat_jid = ?")
                params.append(chat_jid)

            if query:
                where_clauses.append("LOWER(messages.content) LIKE LOWER(?)")
                params.append(f"%{query}%")

            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))

            # Add pagination
            offset = page * limit
            query_parts.append("ORDER BY messages.timestamp DESC")
            query_parts.append("LIMIT ? OFFSET ?")
            params.extend([limit, offset])

            self.conn.execute(" ".join(query_parts), tuple(params))
            messages = self.conn.fetchall()

            result = []
            for msg in messages:
                message = Message(
                    timestamp=datetime.fromisoformat(msg[0]),
                    sender=msg[1],
                    chat_name=msg[2],
                    content=msg[3],
                    is_from_me=msg[4],
                    chat_jid=msg[5],
                    id=msg[6],
                    media_type=msg[7]
                )
                result.append(message)

            if include_context and result:
                # Add context for each message
                messages_with_context = []
                for msg in result:
                    context = self.get_message_context(msg.id, context_before, context_after)
                    messages_with_context.extend(context.before)
                    messages_with_context.append(context.message)
                    messages_with_context.extend(context.after)

                return messages_with_context

            # Return messages without context
            return result

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def get_message_context(
        self,
        message_id: str,
        before: int = 5,
        after: int = 5
    ) -> MessageContext:
        """Retrieve a message with surrounding context."""
        try:
            # Get the target message first
            self.conn.execute("""
                SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.chat_jid, messages.media_type
                FROM messages
                JOIN chats ON messages.chat_jid = chats.jid
                WHERE messages.id = ?
            """, (message_id,))
            msg_data = self.conn.fetchone()

            if not msg_data:
                raise ValueError(f"Message with ID {message_id} not found")

            target_message = Message(
                timestamp=datetime.fromisoformat(msg_data[0]),
                sender=msg_data[1],
                chat_name=msg_data[2],
                content=msg_data[3],
                is_from_me=msg_data[4],
                chat_jid=msg_data[5],
                id=msg_data[6],
                media_type=msg_data[8]
            )

            # Get messages before
            self.conn.execute("""
                SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type
                FROM messages
                JOIN chats ON messages.chat_jid = chats.jid
                WHERE messages.chat_jid = ? AND messages.timestamp < ?
                ORDER BY messages.timestamp DESC
                LIMIT ?
            """, (msg_data[7], msg_data[0], before))

            before_messages = []
            for msg in self.conn.fetchall():
                before_messages.append(Message(
                    timestamp=datetime.fromisoformat(msg[0]),
                    sender=msg[1],
                    chat_name=msg[2],
                    content=msg[3],
                    is_from_me=msg[4],
                    chat_jid=msg[5],
                    id=msg[6],
                    media_type=msg[7]
                ))

            # Get messages after
            self.conn.execute("""
                SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type
                FROM messages
                JOIN chats ON messages.chat_jid = chats.jid
                WHERE messages.chat_jid = ? AND messages.timestamp > ?
                ORDER BY messages.timestamp ASC
                LIMIT ?
            """, (msg_data[7], msg_data[0], after))

            after_messages = []
            for msg in self.conn.fetchall():
                after_messages.append(Message(
                    timestamp=datetime.fromisoformat(msg[0]),
                    sender=msg[1],
                    chat_name=msg[2],
                    content=msg[3],
                    is_from_me=msg[4],
                    chat_jid=msg[5],
                    id=msg[6],
                    media_type=msg[7]
                ))

            return MessageContext(
                message=target_message,
                before=before_messages,
                after=after_messages
            )

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise


class SQLiteChatRepository:
    """SQLite implementation of ChatRepository protocol."""

    def __init__(self, conn: SQLiteConnection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection to messages database
        """
        self.conn = conn

    def list_chats(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        page: int = 0,
        include_last_message: bool = True,
        sort_by: str = "last_active"
    ) -> List[Chat]:
        """Retrieve chats matching the specified criteria."""
        try:
            # Build base query
            query_parts = ["""
                SELECT
                    chats.jid,
                    chats.name,
                    chats.last_message_time,
                    messages.content as last_message,
                    messages.sender as last_sender,
                    messages.is_from_me as last_is_from_me
                FROM chats
            """]

            if include_last_message:
                query_parts.append("""
                    LEFT JOIN messages ON chats.jid = messages.chat_jid
                    AND chats.last_message_time = messages.timestamp
                """)

            where_clauses = []
            params = []

            if query:
                where_clauses.append("(LOWER(chats.name) LIKE LOWER(?) OR chats.jid LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])

            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))

            # Add sorting
            order_by = "chats.last_message_time DESC" if sort_by == "last_active" else "chats.name"
            query_parts.append(f"ORDER BY {order_by}")

            # Add pagination
            offset = page * limit
            query_parts.append("LIMIT ? OFFSET ?")
            params.extend([limit, offset])

            self.conn.execute(" ".join(query_parts), tuple(params))
            chats = self.conn.fetchall()

            result = []
            for chat_data in chats:
                chat = Chat(
                    jid=chat_data[0],
                    name=chat_data[1],
                    last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                    last_message=chat_data[3],
                    last_sender=chat_data[4],
                    last_is_from_me=chat_data[5]
                )
                result.append(chat)

            return result

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def get_chat(
        self,
        chat_jid: str,
        include_last_message: bool = True
    ) -> Optional[Chat]:
        """Retrieve a single chat by JID."""
        try:
            query = """
                SELECT
                    c.jid,
                    c.name,
                    c.last_message_time,
                    m.content as last_message,
                    m.sender as last_sender,
                    m.is_from_me as last_is_from_me
                FROM chats c
            """

            if include_last_message:
                query += """
                    LEFT JOIN messages m ON c.jid = m.chat_jid
                    AND c.last_message_time = m.timestamp
                """

            query += " WHERE c.jid = ?"

            self.conn.execute(query, (chat_jid,))
            chat_data = self.conn.fetchone()

            if not chat_data:
                return None

            return Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5]
            )

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def get_direct_chat_by_contact(
        self,
        sender_phone_number: str
    ) -> Optional[Chat]:
        """Retrieve a direct (non-group) chat by contact phone number."""
        try:
            self.conn.execute("""
                SELECT
                    c.jid,
                    c.name,
                    c.last_message_time,
                    m.content as last_message,
                    m.sender as last_sender,
                    m.is_from_me as last_is_from_me
                FROM chats c
                LEFT JOIN messages m ON c.jid = m.chat_jid
                    AND c.last_message_time = m.timestamp
                WHERE c.jid LIKE ? AND c.jid NOT LIKE '%@g.us'
                LIMIT 1
            """, (f"%{sender_phone_number}%",))

            chat_data = self.conn.fetchone()

            if not chat_data:
                return None

            return Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5]
            )

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None


class SQLiteContactRepository:
    """SQLite implementation of ContactRepository protocol."""

    def __init__(self, conn: SQLiteConnection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection to messages database
        """
        self.conn = conn

    def search_contacts(self, query: str) -> List[Contact]:
        """Search for contacts by name or phone number."""
        try:
            # Split query into characters to support partial matching
            search_pattern = '%' + query + '%'

            self.conn.execute("""
                SELECT DISTINCT
                    jid,
                    name
                FROM chats
                WHERE
                    (LOWER(name) LIKE LOWER(?) OR LOWER(jid) LIKE LOWER(?))
                    AND jid NOT LIKE '%@g.us'
                ORDER BY name, jid
                LIMIT 50
            """, (search_pattern, search_pattern))

            contacts = self.conn.fetchall()

            result = []
            for contact_data in contacts:
                contact = Contact(
                    phone_number=contact_data[0].split('@')[0],
                    name=contact_data[1],
                    jid=contact_data[0]
                )
                result.append(contact)

            return result

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def get_contact_chats(
        self,
        jid: str,
        limit: int = 20,
        page: int = 0
    ) -> List[Chat]:
        """Retrieve all chats involving a specific contact."""
        try:
            self.conn.execute("""
                SELECT DISTINCT
                    c.jid,
                    c.name,
                    c.last_message_time,
                    m.content as last_message,
                    m.sender as last_sender,
                    m.is_from_me as last_is_from_me
                FROM chats c
                JOIN messages m ON c.jid = m.chat_jid
                WHERE m.sender = ? OR c.jid = ?
                ORDER BY c.last_message_time DESC
                LIMIT ? OFFSET ?
            """, (jid, jid, limit, page * limit))

            chats = self.conn.fetchall()

            result = []
            for chat_data in chats:
                chat = Chat(
                    jid=chat_data[0],
                    name=chat_data[1],
                    last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                    last_message=chat_data[3],
                    last_sender=chat_data[4],
                    last_is_from_me=chat_data[5]
                )
                result.append(chat)

            return result

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def get_last_interaction(self, jid: str) -> Optional[Message]:
        """Retrieve the most recent message involving a contact."""
        try:
            self.conn.execute("""
                SELECT
                    m.timestamp,
                    m.sender,
                    c.name,
                    m.content,
                    m.is_from_me,
                    c.jid,
                    m.id,
                    m.media_type
                FROM messages m
                JOIN chats c ON m.chat_jid = c.jid
                WHERE m.sender = ? OR c.jid = ?
                ORDER BY m.timestamp DESC
                LIMIT 1
            """, (jid, jid))

            msg_data = self.conn.fetchone()

            if not msg_data:
                return None

            message = Message(
                timestamp=datetime.fromisoformat(msg_data[0]),
                sender=msg_data[1],
                chat_name=msg_data[2],
                content=msg_data[3],
                is_from_me=msg_data[4],
                chat_jid=msg_data[5],
                id=msg_data[6],
                media_type=msg_data[7]
            )

            return message

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None


class SQLiteAuthenticationRepository:
    """SQLite implementation of AuthenticationRepository protocol."""

    def __init__(self, conn: SQLiteConnection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection to authentication database
        """
        self.conn = conn

    def check_authentication_status(self) -> Tuple[bool, Optional[str]]:
        """Check if WhatsApp is authenticated by looking for session data."""
        try:
            # Check if device table exists and has data
            self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whatsmeow_device';")
            if not self.conn.fetchone():
                return False, "No device table found"

            self.conn.execute("SELECT COUNT(*) FROM whatsmeow_device;")
            device_count = self.conn.fetchone()[0]

            if device_count == 0:
                return False, "No device registered"

            return True, None

        except sqlite3.Error as e:
            return False, f"Database error: {e}"


class SQLiteDatabaseAdapter:
    """SQLite implementation of DatabaseAdapter protocol.

    Provides access to all repository interfaces and manages connections
    to both the messages and authentication databases.
    """

    def __init__(self, messages_db_path: str, auth_db_path: str):
        """Initialize the SQLite database adapter.

        Args:
            messages_db_path: Path to messages database, or ':memory:' for in-memory
            auth_db_path: Path to authentication database, or ':memory:' for in-memory
        """
        self.messages_db_path = messages_db_path
        self.auth_db_path = auth_db_path

        # Initialize connections
        self._messages_conn = SQLiteConnection(messages_db_path)
        self._auth_conn = SQLiteConnection(auth_db_path)

        # Connect immediately
        self._messages_conn.connect()
        self._auth_conn.connect()

        # Initialize repositories
        self._messages = SQLiteMessageRepository(self._messages_conn)
        self._chats = SQLiteChatRepository(self._messages_conn)
        self._contacts = SQLiteContactRepository(self._messages_conn)
        self._authentication = SQLiteAuthenticationRepository(self._auth_conn)

    @property
    def messages(self) -> SQLiteMessageRepository:
        """Access the message repository."""
        return self._messages

    @property
    def chats(self) -> SQLiteChatRepository:
        """Access the chat repository."""
        return self._chats

    @property
    def contacts(self) -> SQLiteContactRepository:
        """Access the contact repository."""
        return self._contacts

    @property
    def authentication(self) -> SQLiteAuthenticationRepository:
        """Access the authentication repository."""
        return self._authentication

    def unit_of_work(self) -> SQLiteUnitOfWork:
        """Create a new unit of work for transactional operations."""
        return SQLiteUnitOfWork(self._messages_conn, self._auth_conn)

    def close(self) -> None:
        """Close all connections and release resources."""
        self._messages_conn.close()
        self._auth_conn.close()
