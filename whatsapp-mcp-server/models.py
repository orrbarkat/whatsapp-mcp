"""Domain models for the WhatsApp MCP server.

This module contains the core dataclasses used throughout the application.
These models represent the domain entities and are used by both the business
logic and the data access layer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Message:
    """Represents a WhatsApp message.

    Attributes:
        timestamp: When the message was sent/received
        sender: JID of the message sender
        content: Text content of the message
        is_from_me: Whether the message was sent by the authenticated user
        chat_jid: JID of the chat this message belongs to
        id: Unique message identifier
        chat_name: Display name of the chat (optional)
        media_type: Type of media attachment if any (optional)
    """
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_jid: str
    id: str
    chat_name: Optional[str] = None
    media_type: Optional[str] = None


@dataclass
class Chat:
    """Represents a WhatsApp chat (direct or group).

    Attributes:
        jid: Unique chat identifier (JID)
        name: Display name of the chat
        last_message_time: Timestamp of the most recent message
        last_message: Content of the most recent message (optional)
        last_sender: JID of the sender of the last message (optional)
        last_is_from_me: Whether the last message was sent by the authenticated user (optional)
    """
    jid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None

    @property
    def is_group(self) -> bool:
        """Determine if chat is a group based on JID pattern.

        Returns:
            True if the chat is a group chat, False otherwise
        """
        return self.jid.endswith("@g.us")


@dataclass
class Contact:
    """Represents a WhatsApp contact.

    Attributes:
        phone_number: Phone number of the contact (without JID suffix)
        name: Display name of the contact
        jid: Full JID of the contact
    """
    phone_number: str
    name: Optional[str]
    jid: str


@dataclass
class MessageContext:
    """Represents a message with its surrounding context.

    Used to provide conversation context around a specific message.

    Attributes:
        message: The target message
        before: List of messages that came before the target message
        after: List of messages that came after the target message
    """
    message: Message
    before: List[Message]
    after: List[Message]


@dataclass
class BridgeStatus:
    """Represents the status of the WhatsApp bridge service.

    Attributes:
        is_running: Whether the bridge process is running
        is_authenticated: Whether WhatsApp is authenticated
        api_responsive: Whether the bridge API is responding
        qr_code: QR code data for authentication (optional)
        error_message: Error message if any (optional)
    """
    is_running: bool
    is_authenticated: bool
    api_responsive: bool
    qr_code: Optional[str] = None
    error_message: Optional[str] = None
