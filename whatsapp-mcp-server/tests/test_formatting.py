import datetime as dt
from whatsapp import Message, format_message, format_messages_list


def test_format_message_me_simple():
    m = Message(
        timestamp=dt.datetime(2024, 1, 2, 3, 4, 5),
        sender="123456789",
        content="hello",
        is_from_me=True,
        chat_jid="123456789@s.whatsapp.net",
        id="abc123",
        chat_name="Alice",
        media_type=None,
    )
    out = format_message(m)
    assert "[2024-01-02 03:04:05]" in out
    assert "From: Me" in out
    assert out.rstrip().endswith(": hello")


def test_format_message_media_prefix():
    m = Message(
        timestamp=dt.datetime(2024, 1, 2, 3, 4, 5),
        sender="123456789",
        content="photo caption",
        is_from_me=True,
        chat_jid="123456789@s.whatsapp.net",
        id="m1",
        chat_name="Alice",
        media_type="image",
    )
    out = format_message(m)
    assert "[image - Message ID: m1 - Chat JID: 123456789@s.whatsapp.net]" in out


def test_format_messages_list_empty():
    out = format_messages_list([])
    assert out == "No messages to display."
