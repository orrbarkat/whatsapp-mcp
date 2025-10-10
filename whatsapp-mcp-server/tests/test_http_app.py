import pytest
import sqlite3
from datetime import datetime, timedelta

try:
    from fastapi.testclient import TestClient
    fastapi_available = True
except Exception:  # pragma: no cover
    fastapi_available = False

def populate_db_with_sample_data(db_path: str):
    """Populate the database with sample data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Insert sample chat data
        sample_chats = [
            ("123456789@s.whatsapp.net", "Alice Smith", "2024-01-10 10:30:00"),
            ("987654321@s.whatsapp.net", "Bob Johnson", "2024-01-09 15:45:00"),
            ("555666777@s.whatsapp.net", "Charlie Brown", "2024-01-08 09:15:00"),
            ("123456789-group@g.us", "Work Team", "2024-01-10 14:20:00"),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO chats (jid, name, last_message_time) VALUES (?, ?, ?)",
            sample_chats,
        )

        # Insert sample message data
        base_time = datetime(2024, 1, 10, 10, 0, 0)
        sample_messages = [
            # Messages with Alice
            (
                "msg1",
                (base_time + timedelta(minutes=1)).isoformat(),
                "123456789@s.whatsapp.net",
                "Hello there!",
                0,
                "123456789@s.whatsapp.net",
                None,
            ),
            (
                "msg2",
                (base_time + timedelta(minutes=2)).isoformat(),
                "me",
                "Hi Alice! How are you?",
                1,
                "123456789@s.whatsapp.net",
                None,
            ),
            (
                "msg3",
                (base_time + timedelta(minutes=30)).isoformat(),
                "123456789@s.whatsapp.net",
                "I'm doing great, thanks!",
                0,
                "123456789@s.whatsapp.net",
                None,
            ),
            # Messages with Bob
            (
                "msg4",
                (base_time - timedelta(hours=1)).isoformat(),
                "987654321@s.whatsapp.net",
                "Can you review the document?",
                0,
                "987654321@s.whatsapp.net",
                None,
            ),
            (
                "msg5",
                (base_time - timedelta(minutes=50)).isoformat(),
                "me",
                "Sure, I'll take a look",
                1,
                "987654321@s.whatsapp.net",
                None,
            ),
            # Messages with Charlie
            (
                "msg6",
                (base_time - timedelta(days=2)).isoformat(),
                "555666777@s.whatsapp.net",
                "Weekend plans?",
                0,
                "555666777@s.whatsapp.net",
                None,
            ),
            (
                "msg7",
                (base_time - timedelta(days=2) + timedelta(hours=1)).isoformat(),
                "me",
                "Nothing special, you?",
                1,
                "555666777@s.whatsapp.net",
                None,
            ),
            # Group messages
            (
                "msg8",
                (base_time + timedelta(hours=4)).isoformat(),
                "123456789@s.whatsapp.net",
                "Team meeting at 3pm",
                0,
                "123456789-group@g.us",
                None,
            ),
            (
                "msg9",
                (base_time + timedelta(hours=4, minutes=5)).isoformat(),
                "987654321@s.whatsapp.net",
                "I'll be there",
                0,
                "123456789-group@g.us",
                None,
            ),
            (
                "msg10",
                (base_time + timedelta(hours=4, minutes=10)).isoformat(),
                "me",
                "Same here",
                1,
                "123456789-group@g.us",
                None,
            ),
            # Message with media
            (
                "msg11",
                (base_time + timedelta(hours=5)).isoformat(),
                "123456789@s.whatsapp.net",
                "Check out this photo!",
                0,
                "123456789@s.whatsapp.net",
                "image",
            ),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO messages (id, timestamp, sender, content, is_from_me, chat_jid, media_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            sample_messages,
        )
        conn.commit()
    finally:
        conn.close()

@pytest.fixture
def populated_db(test_db_with_reload):
    """Provide a test database with sample data."""
    db_path = test_db_with_reload
    populate_db_with_sample_data(db_path)
    return db_path

def test_search_contacts_endpoint(populated_db):
    import server as m

    app = m.create_app()
    client = TestClient(app)

    resp = client.post("/search_contacts", json={"query": "Alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["jid"] == "123456789@s.whatsapp.net"
    assert data[0]["name"] == "Alice Smith"
    assert data[0]["phone_number"] == "123456789"
