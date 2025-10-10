"""
Test utilities for database testing.
"""
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from typing import Generator, List
from contextlib import contextmanager

def create_db_schema(db_path: str) -> None:
    """Create the database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Create the chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                jid TEXT PRIMARY KEY,
                name TEXT,
                last_message_time TEXT
            )
        """)
        
        # Create the messages table  
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                sender TEXT,
                content TEXT,
                is_from_me INTEGER,
                chat_jid TEXT,
                media_type TEXT,
                FOREIGN KEY (chat_jid) REFERENCES chats (jid)
            )
        """)
        conn.commit()
    finally:
        conn.close()

@contextmanager
def temp_test_db() -> Generator[str, None, None]:
    """Create a temporary test database with schema and yield its path."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        db_path = temp_file.name
    
    try:
        create_db_schema(db_path)
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

def get_sample_contacts() -> List[dict]:
    """Return expected sample contact data for tests."""
    return [
        {"jid": "123456789@s.whatsapp.net", "name": "Alice Smith", "phone_number": "123456789"},
        {"jid": "987654321@s.whatsapp.net", "name": "Bob Johnson", "phone_number": "987654321"},
        {"jid": "555666777@s.whatsapp.net", "name": "Charlie Brown", "phone_number": "555666777"},
    ]

def get_sample_chats() -> List[dict]:
    """Return expected sample chat data for tests."""
    return [
        {
            "jid": "123456789@s.whatsapp.net", 
            "name": "Alice Smith", 
            "last_message_time": "2024-01-10T10:30:00",
            "is_group": False
        },
        {
            "jid": "987654321@s.whatsapp.net", 
            "name": "Bob Johnson", 
            "last_message_time": "2024-01-09T15:45:00",
            "is_group": False
        },
        {
            "jid": "555666777@s.whatsapp.net", 
            "name": "Charlie Brown", 
            "last_message_time": "2024-01-08T09:15:00", 
            "is_group": False
        },
        {
            "jid": "123456789-group@g.us", 
            "name": "Work Team", 
            "last_message_time": "2024-01-10T14:20:00",
            "is_group": True
        },
    ]

def get_sample_messages() -> List[dict]:
    """Return expected sample message data for tests."""
    base_time = datetime(2024, 1, 10, 10, 0, 0)
    return [
        {
            "id": "msg1",
            "timestamp": base_time + timedelta(minutes=1),
            "sender": "123456789@s.whatsapp.net", 
            "content": "Hello there!",
            "is_from_me": False,
            "chat_jid": "123456789@s.whatsapp.net",
            "media_type": None
        },
        {
            "id": "msg2",
            "timestamp": base_time + timedelta(minutes=2),
            "sender": "me", 
            "content": "Hi Alice! How are you?",
            "is_from_me": True,
            "chat_jid": "123456789@s.whatsapp.net",
            "media_type": None
        }
        # Add more as needed for specific tests
    ]