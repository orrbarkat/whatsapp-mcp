from typing import List, Dict, Any, Optional
import os
import argparse
from mcp.server.fastmcp import FastMCP
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media
)

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except Exception:
    FastAPI = None  # type: ignore
    BaseModel = object  # type: ignore

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

# -------- HTTP transport (optional) --------
class _SearchContactsReq(BaseModel):
    query: str

class _ListMessagesReq(BaseModel):
    after: Optional[str] = None
    before: Optional[str] = None
    sender_phone_number: Optional[str] = None
    chat_jid: Optional[str] = None
    query: Optional[str] = None
    limit: int = 20
    page: int = 0
    include_context: bool = True
    context_before: int = 1
    context_after: int = 1

class _ListChatsReq(BaseModel):
    query: Optional[str] = None
    limit: int = 20
    page: int = 0
    include_last_message: bool = True
    sort_by: str = "last_active"

class _GetChatReq(BaseModel):
    chat_jid: str
    include_last_message: bool = True

class _GetDirectChatReq(BaseModel):
    sender_phone_number: str

class _GetContactChatsReq(BaseModel):
    jid: str
    limit: int = 20
    page: int = 0

class _GetLastInteractionReq(BaseModel):
    jid: str

class _GetMessageContextReq(BaseModel):
    message_id: str
    before: int = 5
    after: int = 5

class _SendMessageReq(BaseModel):
    recipient: str
    message: str

class _SendFileReq(BaseModel):
    recipient: str
    media_path: str

class _DownloadMediaReq(BaseModel):
    message_id: str
    chat_jid: str


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed; install extras to enable HTTP transport")
    app = FastAPI()

    @app.post("/search_contacts")
    def http_search_contacts(req: _SearchContactsReq):
        return search_contacts(req.query)

    @app.post("/list_messages")
    def http_list_messages(req: _ListMessagesReq):
        return list_messages(
            after=req.after,
            before=req.before,
            sender_phone_number=req.sender_phone_number,
            chat_jid=req.chat_jid,
            query=req.query,
            limit=req.limit,
            page=req.page,
            include_context=req.include_context,
            context_before=req.context_before,
            context_after=req.context_after,
        )

    @app.post("/list_chats")
    def http_list_chats(req: _ListChatsReq):
        return list_chats(
            query=req.query,
            limit=req.limit,
            page=req.page,
            include_last_message=req.include_last_message,
            sort_by=req.sort_by,
        )

    @app.post("/get_chat")
    def http_get_chat(req: _GetChatReq):
        return get_chat(req.chat_jid, req.include_last_message)

    @app.post("/get_direct_chat_by_contact")
    def http_get_direct_chat_by_contact(req: _GetDirectChatReq):
        return get_direct_chat_by_contact(req.sender_phone_number)

    @app.post("/get_contact_chats")
    def http_get_contact_chats(req: _GetContactChatsReq):
        return get_contact_chats(req.jid, req.limit, req.page)

    @app.post("/get_last_interaction")
    def http_get_last_interaction(req: _GetLastInteractionReq):
        return get_last_interaction(req.jid)

    @app.post("/get_message_context")
    def http_get_message_context(req: _GetMessageContextReq):
        return get_message_context(req.message_id, req.before, req.after)

    @app.post("/send_message")
    def http_send_message(req: _SendMessageReq):
        return send_message(req.recipient, req.message)

    @app.post("/send_file")
    def http_send_file(req: _SendFileReq):
        return send_file(req.recipient, req.media_path)

    @app.post("/send_audio_message")
    def http_send_audio_message(req: _SendFileReq):
        return send_audio_message(req.recipient, req.media_path)

    @app.post("/download_media")
    def http_download_media(req: _DownloadMediaReq):
        return download_media(req.message_id, req.chat_jid)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
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
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], default=os.getenv("TRANSPORT_MODE", "stdio"))
    args = parser.parse_args()

    if args.transport == "http":
        if FastAPI is None:
            raise RuntimeError("FastAPI is not installed; cannot run HTTP transport. Install fastapi/uvicorn.")
        app = create_app()
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
    else:
        # Initialize and run the server in stdio mode (default)
        mcp.run(transport='stdio')
