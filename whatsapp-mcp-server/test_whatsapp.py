import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from whatsapp import (
    Message,
    get_sender_name,
    list_messages,
    send_audio_message,
    send_file,
    send_message,
)


@patch("sqlite3.connect")
def test_get_sender_name_found(mock_connect):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("John Doe",)
    mock_connect.return_value.cursor.return_value = mock_cursor

    assert get_sender_name("12345@s.whatsapp.net") == "John Doe"
    mock_cursor.execute.assert_called()


@patch("sqlite3.connect")
def test_get_sender_name_not_found(mock_connect):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_connect.return_value.cursor.return_value = mock_cursor

    assert get_sender_name("12345@s.whatsapp.net") == "12345@s.whatsapp.net"


@patch("whatsapp.get_message_context")
@patch("sqlite3.connect")
def test_list_messages_success(mock_connect, mock_get_context):
    mock_get_context.return_value = MagicMock(
        before=[],
        after=[],
        message=Message(
            timestamp=datetime.now(),
            sender="sender1",
            content="Hello",
            is_from_me=False,
            chat_jid="chat1",
            id="msg1",
        ),
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        (
            "2023-01-01T12:00:00",
            "sender1",
            "Chat 1",
            "Hello",
            False,
            "chat1",
            "msg1",
            None,
        )
    ]
    mock_connect.return_value.cursor.return_value = mock_cursor

    messages = list_messages(limit=1)
    assert "Hello" in messages


@patch("requests.post")
def test_send_message_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "message": "Sent"}
    mock_post.return_value = mock_response

    success, message = send_message("12345", "Hello")
    assert success is True
    assert message == "Sent"


@patch("requests.post")
def test_send_message_failure(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Error"
    mock_post.return_value = mock_response

    success, message = send_message("12345", "Hello")
    assert success is False
    assert "Error" in message


@patch("os.path.isfile")
@patch("requests.post")
def test_send_file_success(mock_post, mock_isfile):
    mock_isfile.return_value = True
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "message": "Sent"}
    mock_post.return_value = mock_response

    success, message = send_file("12345", "/path/to/file")
    assert success is True
    assert message == "Sent"


@patch("os.path.isfile")
def test_send_file_not_found(mock_isfile):
    mock_isfile.return_value = False
    success, message = send_file("12345", "/path/to/file")
    assert success is False
    assert "not found" in message


@patch("audio.convert_to_opus_ogg_temp")
@patch("os.path.isfile")
@patch("requests.post")
def test_send_audio_message_success(mock_post, mock_isfile, mock_convert):
    mock_isfile.return_value = True
    mock_convert.return_value = "/tmp/audio.ogg"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "message": "Sent"}
    mock_post.return_value = mock_response

    success, message = send_audio_message("12345", "/path/to/audio.mp3")
    assert success is True
    assert message == "Sent"
    mock_convert.assert_called_once_with("/path/to/audio.mp3")


@patch("audio.convert_to_opus_ogg_temp")
@patch("os.path.isfile")
def test_send_audio_message_conversion_fails(mock_isfile, mock_convert):
    mock_isfile.return_value = True
    mock_convert.side_effect = RuntimeError("Conversion failed")

    success, message = send_audio_message("12345", "/path/to/audio.mp3")
    assert success is False
    assert "Error converting file" in message
