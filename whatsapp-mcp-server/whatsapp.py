from datetime import datetime
from typing import Optional, List, Tuple
import os
import atexit
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import audio
import subprocess
import time
import threading
import queue
import psutil
import signal
from models import Message, Chat, Contact, MessageContext, BridgeStatus
from database_sqlite import SQLiteDatabaseAdapter

MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'messages.db')
WHATSAPP_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'whatsapp.db')
WHATSAPP_API_BASE_URL = "http://localhost:8080/api"
BRIDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge')
BRIDGE_EXECUTABLE = "whatsapp-bridge"
BRIDGE_PROCESS = None
BRIDGE_OUTPUT_QUEUE = queue.Queue()
QR_CODE_DATA = None

# Configure HTTP session with retries and timeouts
_http_session = None

def get_http_session() -> requests.Session:
    """Get or create HTTP session with retries and timeouts configured."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        # Configure retry strategy: 3 retries, backoff factor of 0.3s
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _http_session.mount("http://", adapter)
        _http_session.mount("https://", adapter)
    return _http_session

# Default timeout: 3s connect, 15s read
DEFAULT_TIMEOUT = (3, 15)

# Initialize database adapter
_db_adapter: Optional[SQLiteDatabaseAdapter] = None

def get_db_adapter() -> SQLiteDatabaseAdapter:
    """Get or create the database adapter instance."""
    global _db_adapter
    if _db_adapter is None:
        _db_adapter = SQLiteDatabaseAdapter(MESSAGES_DB_PATH, WHATSAPP_DB_PATH)
    return _db_adapter

def get_sender_name(sender_jid: str) -> str:
    adapter = get_db_adapter()
    return adapter.messages.get_sender_name(sender_jid)

def format_message(message: Message, show_chat_info: bool = True) -> None:
    """Print a single message with consistent formatting."""
    output = ""
    
    if show_chat_info and message.chat_name:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] Chat: {message.chat_name} "
    else:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] "
        
    content_prefix = ""
    if hasattr(message, 'media_type') and message.media_type:
        content_prefix = f"[{message.media_type} - Message ID: {message.id} - Chat JID: {message.chat_jid}] "
    
    try:
        sender_name = get_sender_name(message.sender) if not message.is_from_me else "Me"
        output += f"From: {sender_name}: {content_prefix}{message.content}\n"
    except Exception as e:
        print(f"Error formatting message: {e}")
    return output

def format_messages_list(messages: List[Message], show_chat_info: bool = True) -> None:
    output = ""
    if not messages:
        output += "No messages to display."
        return output
    
    for message in messages:
        output += format_message(message, show_chat_info)
    return output

# Bridge Management Functions

def is_bridge_process_running() -> bool:
    """Check if the bridge Go process is currently running."""
    global BRIDGE_PROCESS
    
    if BRIDGE_PROCESS and BRIDGE_PROCESS.poll() is None:
        return True
    
    # Check if any process is running the bridge executable
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] and 'whatsapp-bridge' in proc.info['exe']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return False

def check_api_health() -> bool:
    """Check if the bridge API is responsive."""
    try:
        session = get_http_session()
        response = session.get(f"{WHATSAPP_API_BASE_URL.replace('/api', '')}/health", timeout=DEFAULT_TIMEOUT)
        return response.status_code == 200
    except requests.RequestException:
        return False

def check_authentication_status() -> Tuple[bool, Optional[str]]:
    """Check if WhatsApp is authenticated.

    First tries the bridge API for most accurate status, then falls back to
    database checks. This works with both SQLite and Postgres session storage.
    """
    # Try bridge API first (most reliable)
    try:
        session = get_http_session()
        response = session.get(f"{WHATSAPP_API_BASE_URL}/auth-status", timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get("authenticated"):
                return True, "Authenticated via bridge"
            elif data.get("has_qr_code"):
                return False, "QR code available for scanning"
            else:
                return False, "Not authenticated"
    except requests.RequestException as e:
        # Bridge not available, fall back to database check
        pass

    # Fall back to database check if bridge API is unavailable
    # This works with both SQLite and Postgres using the unified adapter
    try:
        from config import get_database_adapter
        adapter = get_database_adapter()
        return adapter.authentication.check_authentication_status()
    except Exception as e:
        # If database check also fails, assume not authenticated
        return False, f"Unable to check authentication: {str(e)}"

def monitor_bridge_output(process):
    """Monitor bridge process output for QR codes and status updates."""
    global QR_CODE_DATA, BRIDGE_OUTPUT_QUEUE
    
    qr_lines = []
    capturing_qr = False
    
    for line in iter(process.stdout.readline, ''):
        line_str = line.strip()
        BRIDGE_OUTPUT_QUEUE.put(line_str)
        
        # Detect QR code start
        if "Scan this QR code with your WhatsApp app:" in line_str:
            capturing_qr = True
            qr_lines = []
            continue
        
        # Capture QR code lines (they contain █ and ▄ characters)
        if capturing_qr:
            if "Successfully connected and authenticated!" in line_str:
                capturing_qr = False
                if qr_lines:
                    QR_CODE_DATA = "\n".join(qr_lines)
            elif any(char in line_str for char in ['█', '▄', '▀', '▐', '▌']):
                qr_lines.append(line_str)

def start_bridge_process() -> Tuple[bool, str]:
    """Start the WhatsApp bridge Go process."""
    global BRIDGE_PROCESS
    
    if is_bridge_process_running():
        return True, "Bridge is already running"
    
    try:
        # Change to bridge directory and start the Go application
        bridge_path = os.path.abspath(BRIDGE_DIR)
        
        if not os.path.exists(bridge_path):
            return False, f"Bridge directory not found: {bridge_path}"
        
        executable_path = os.path.join(bridge_path, BRIDGE_EXECUTABLE)
        if not os.path.exists(executable_path):
            return False, f"Bridge executable not found: {executable_path}"
        
        # Make sure the binary is executable
        os.chmod(executable_path, 0o755)

        # Start the process
        # Start in a new session for proper signal handling in Cloud Run
        BRIDGE_PROCESS = subprocess.Popen(
            [executable_path],
            cwd=bridge_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        
        # Start output monitoring in a separate thread
        output_thread = threading.Thread(target=monitor_bridge_output, args=(BRIDGE_PROCESS,))
        output_thread.daemon = True
        output_thread.start()
        
        # Wait a moment for the process to start and check for immediate errors
        start_wait_time = time.time()
        error_message = None
        while time.time() - start_wait_time < 5: # Increased wait time to capture more output
            try:
                line = BRIDGE_OUTPUT_QUEUE.get_nowait()
                print(f"Bridge startup output: {line}") # Debug output
                if "Required session table 'devices' does not exist" in line or "Bridge initialization failed" in line:
                    error_message = line
                    break
            except queue.Empty:
                pass
            
            if BRIDGE_PROCESS.poll() is not None:
                # Process exited, capture its return code
                return False, f"Bridge process failed to start. Exit code: {BRIDGE_PROCESS.returncode}. Output: {error_message or 'No specific error message captured.'}"
            
            time.sleep(0.1) # Check more frequently
        
        if error_message:
            return False, f"Bridge initialization failed: {error_message}"
        
        if BRIDGE_PROCESS.poll() is not None:
            return False, f"Bridge process failed to start. Exit code: {BRIDGE_PROCESS.returncode}"
        
        return True, "Bridge process started successfully"
        
    except Exception as e:
        return False, f"Failed to start bridge process: {str(e)}"

def stop_bridge_process() -> bool:
    """Stop the WhatsApp bridge process."""
    global BRIDGE_PROCESS
    if BRIDGE_PROCESS:
        try:
            pid = BRIDGE_PROCESS.pid
            # Try to signal the process group first
            try:
                pgid = os.getpgid(pid)
                print("Sending SIGTERM to bridge process group...", flush=True)
                os.killpg(pgid, signal.SIGTERM)
            except Exception:
                # Fallback to terminating the process directly
                try:
                    BRIDGE_PROCESS.terminate()
                except Exception:
                    pass

            try:
                BRIDGE_PROCESS.wait(timeout=10)
                print("Bridge process terminated gracefully", flush=True)
            except subprocess.TimeoutExpired:
                print("Bridge did not exit in time; sending SIGKILL...", flush=True)
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except Exception:
                    try:
                        BRIDGE_PROCESS.kill()
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error stopping bridge process: {e}", flush=True)
        finally:
            BRIDGE_PROCESS = None

    return True

def wait_for_authentication(timeout: int = 120) -> Tuple[bool, Optional[str]]:
    """Wait for WhatsApp authentication to complete."""
    global QR_CODE_DATA, BRIDGE_OUTPUT_QUEUE
    
    start_time = time.time()
    qr_returned = False
    collected_output = []
    
    while time.time() - start_time < timeout:
        # Check authentication status first
        is_auth, _ = check_authentication_status()
        if is_auth:
            return True, None
        
        # Check for new output from bridge
        try:
            while True:
                line = BRIDGE_OUTPUT_QUEUE.get_nowait()
                collected_output.append(line)
                print(f"Bridge output: {line}")  # Debug output
        except queue.Empty:
            pass
        
        # Check if we have a QR code to display (only return it once)
        if QR_CODE_DATA and not qr_returned:
            qr_returned = True
            return False, QR_CODE_DATA
        
        # Look for QR code patterns in collected output
        output_text = '\n'.join(collected_output)
        if "Scan this QR code with your WhatsApp app:" in output_text and not qr_returned:
            # Extract QR code lines manually
            qr_lines = []
            in_qr = False
            for line in collected_output:
                if "Scan this QR code with your WhatsApp app:" in line:
                    in_qr = True
                    continue
                if in_qr:
                    if any(char in line for char in ['█', '▄', '▀', '▐', '▌']):
                        qr_lines.append(line)
                    elif "Successfully connected" in line or "Connected to WhatsApp" in line:
                        break
            
            if qr_lines:
                qr_code = '\n'.join(qr_lines)
                qr_returned = True
                return False, qr_code
        
        # Check if bridge process is still running
        if not is_bridge_process_running():
            return False, "Bridge process stopped unexpectedly"
        
        time.sleep(0.5)  # Check more frequently
    
    # Return collected output for debugging if timeout
    debug_info = f"Authentication timeout. Collected output:\n" + '\n'.join(collected_output[-20:])  # Last 20 lines
    return False, debug_info

def get_bridge_status() -> BridgeStatus:
    """Get comprehensive bridge status."""
    is_running = is_bridge_process_running()
    api_responsive = check_api_health() if is_running else False
    is_authenticated, auth_error = check_authentication_status()
    
    status = BridgeStatus(
        is_running=is_running,
        is_authenticated=is_authenticated,
        api_responsive=api_responsive,
        error_message=auth_error
    )
    
    return status

def get_qr_code_from_running_bridge() -> Optional[str]:
    """Try to get QR code from a running bridge by restarting it and capturing output."""
    global BRIDGE_PROCESS
    
    # Stop current bridge
    stop_bridge_process()
    time.sleep(1)
    
    try:
        # Start bridge and capture initial output
        bridge_path = os.path.abspath(BRIDGE_DIR)
        executable_path = os.path.join(bridge_path, BRIDGE_EXECUTABLE)

        if not os.path.exists(executable_path):
            return None

        # Make sure the binary is executable
        os.chmod(executable_path, 0o755)

        # Start process and capture output for a few seconds
        process = subprocess.Popen(
            [executable_path],
            cwd=bridge_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        
        output_lines = []
        start_time = time.time()
        
        # Capture output for up to 8 seconds
        while time.time() - start_time < 8:
            try:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    # Check if we found authentication success
                    if "Successfully connected and authenticated" in line:
                        break
                else:
                    time.sleep(0.1)
            except:
                break
        
        # Set the global process reference
        BRIDGE_PROCESS = process
        
        # Extract QR code from output
        qr_lines = []
        in_qr = False
        
        for line in output_lines:
            if "Scan this QR code with your WhatsApp app:" in line:
                in_qr = True
                continue
            if in_qr:
                if any(char in line for char in ['█', '▄', '▀', '▐', '▌']):
                    qr_lines.append(line)
                elif "Successfully connected" in line or "Connected to WhatsApp" in line:
                    break
                elif line.strip() == "":  # End of QR code
                    break
        
        if qr_lines:
            return '\n'.join(qr_lines)
        
        return None
        
    except Exception as e:
        print(f"Error getting QR code: {e}")
        return None

def ensure_bridge_ready() -> Tuple[bool, str, Optional[str]]:
    """Ensure bridge is running and authenticated. Returns (success, message, qr_url)."""
    
    status = get_bridge_status()
    
    # If everything is ready, return success
    if status.is_running and status.api_responsive and status.is_authenticated:
        return True, "Bridge is ready", None
    
    # If bridge is not running, start it
    if not status.is_running:
        success, message = start_bridge_process()
        if not success:
            return False, f"Failed to start bridge: {message}", None
        
        # Wait for API to become responsive
        for _ in range(30):  # Wait up to 30 seconds
            if check_api_health():
                break
            time.sleep(1)
        else:
            return False, "Bridge started but API is not responsive", None
    
    # Check authentication status again after ensuring bridge is running
    status = get_bridge_status()
    if status.is_authenticated:
        return True, "Bridge is ready and authenticated", None
    
    # Not authenticated - bridge should be serving QR code via web interface
    qr_url = "http://localhost:8080/qr"
    return False, "Bridge is running but not authenticated. Please scan the QR code via the web interface.", qr_url

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
) -> List[Message]:
    """Get messages matching the specified criteria with optional context.

    Returns:
        List of Message domain objects. If include_context is True, the list
        will include context messages interleaved with matched messages.
        Callers should use format_messages_list() for display formatting.
    """
    adapter = get_db_adapter()
    return adapter.messages.list_messages(
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


def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> MessageContext:
    """Get context around a specific message."""
    adapter = get_db_adapter()
    return adapter.messages.get_message_context(message_id, before, after)


def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Chat]:
    """Get chats matching the specified criteria."""
    adapter = get_db_adapter()
    return adapter.chats.list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )


def search_contacts(query: str) -> List[Contact]:
    """Search contacts by name or phone number."""
    adapter = get_db_adapter()
    return adapter.contacts.search_contacts(query)


def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Chat]:
    """Get all chats involving the contact.

    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    adapter = get_db_adapter()
    return adapter.contacts.get_contact_chats(jid, limit, page)


def get_last_interaction(jid: str) -> Optional[Message]:
    """Get most recent message involving the contact.

    Returns:
        Message domain object if found, None otherwise.
        Callers should use format_message() for display formatting.
    """
    adapter = get_db_adapter()
    return adapter.contacts.get_last_interaction(jid)


def get_chat(chat_jid: str, include_last_message: bool = True) -> Optional[Chat]:
    """Get chat metadata by JID."""
    adapter = get_db_adapter()
    return adapter.chats.get_chat(chat_jid, include_last_message)


def get_direct_chat_by_contact(sender_phone_number: str) -> Optional[Chat]:
    """Get chat metadata by sender phone number."""
    adapter = get_db_adapter()
    return adapter.chats.get_direct_chat_by_contact(sender_phone_number)

def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"

        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "message": message,
        }

        session = get_http_session()
        response = session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.Timeout:
        return False, "Request timed out. The bridge may be unresponsive."
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_file(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"

        if not media_path:
            return False, "Media path must be provided"

        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }

        session = get_http_session()
        response = session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.Timeout:
        return False, "Request timed out. The bridge may be unresponsive."
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        if not media_path.endswith(".ogg"):
            try:
                media_path = audio.convert_to_opus_ogg_temp(media_path)
            except Exception as e:
                return False, f"Error converting file to opus ogg. You likely need to install ffmpeg: {str(e)}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }

        session = get_http_session()
        response = session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.Timeout:
        return False, "Request timed out. The bridge may be unresponsive."
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def download_media(message_id: str, chat_jid: str) -> Optional[str]:
    """Download media from a message and return the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        The local file path if download was successful, None otherwise
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/download"
        payload = {
            "message_id": message_id,
            "chat_jid": chat_jid
        }

        session = get_http_session()
        response = session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                path = result.get("path")
                print(f"Media downloaded successfully: {path}")
                return path
            else:
                print(f"Download failed: {result.get('message', 'Unknown error')}")
                return None
        else:
            print(f"Error: HTTP {response.status_code} - {response.text}")
            return None

    except requests.Timeout:
        print("Request timed out. The bridge may be unresponsive.")
        return None
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except json.JSONDecodeError:
        print(f"Error parsing response: {response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None


# Ensure bridge is stopped when the Python process exits
atexit.register(stop_bridge_process)
