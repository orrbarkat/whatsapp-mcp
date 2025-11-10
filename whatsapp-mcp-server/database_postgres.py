
"""PostgreSQL implementation of the database repository interfaces.

This module provides concrete PostgreSQL implementations of all repository protocols
defined in database.py. It handles connection management, query execution, and
proper transaction handling.
"""

import psycopg2
from datetime import datetime
from typing import Optional, List, Tuple, Any
from contextlib import contextmanager
from models import Message, Chat, Contact, MessageContext

class PostgresConnection:
    """Manages PostgreSQL database connections with proper lifecycle handling."""

    def __init__(self, db_url: str):
        """Initialize connection manager.

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._cursor: Optional[psycopg2.extensions.cursor] = None

    def connect(self) -> None:
        """Establish a connection to the database."""
        if self._conn is None:
            self._conn = psycopg2.connect(self.db_url)

    def cursor(self) -> psycopg2.extensions.cursor:
        """Create and return a database cursor."""
        if self._conn is None:
            self.connect()
        if self._cursor is None:
            self._cursor = self._conn.cursor()
        return self._cursor

    def execute(self, query: str, params: Optional[Tuple] = None) -> psycopg2.extensions.cursor:
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

class PostgresUnitOfWork:
    """Manages transactions for PostgreSQL operations."""

    def __init__(self, conn: PostgresConnection):
        """Initialize unit of work with a connection.

        Args:
            conn: Connection to the database
        """
        self.conn = conn
        self._in_transaction = False

    def begin(self) -> None:
        """Begin a new transaction."""
        if not self._in_transaction:
            self.conn.execute("BEGIN")
            self._in_transaction = True

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._in_transaction:
            self.conn.commit()
            self._in_transaction = False

    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._in_transaction:
            self.conn.rollback()
            self._in_transaction = False

    def __enter__(self) -> "PostgresUnitOfWork":
        """Enter the transaction context."""
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the transaction context."""
        if exc_type is not None:
            self.rollback()

class PostgresDatabaseAdapter:
    """PostgreSQL implementation of DatabaseAdapter protocol."""

    def __init__(self, db_url: str):
        """Initialize the PostgreSQL database adapter.

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self._conn = PostgresConnection(db_url)
        self._conn.connect()

    def unit_of_work(self) -> PostgresUnitOfWork:
        """Create a new unit of work for transactional operations."""
        return PostgresUnitOfWork(self._conn)

    def close(self) -> None:
        """Close all connections and release resources."""
        self._conn.close()
