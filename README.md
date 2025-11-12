# WhatsApp MCP Server

Connect Claude to your personal WhatsApp account to search messages, send texts, share media, and interact with your contacts using AI.

This Model Context Protocol (MCP) server integrates with WhatsApp Web's multidevice API via the [whatsmeow](https://github.com/tulir/whatsmeow) library. Your messages are stored locally in a database and only sent to an LLM when you explicitly access them through tools.

![WhatsApp MCP Example](./example-use.png)

**What you can do:**
- Search and read message history (including images, videos, documents, and audio)
- Search contacts and get conversation context
- Send messages to individuals or groups
- Send and download media files
- Monitor connection status and sync progress

> **Note**: To get updates on this and other projects, [enter your email here](https://docs.google.com/forms/d/1rTF9wMBTN0vPfzWuQa2BjfGKdKIpTbyeKxhPMcEzgyI/preview)

> **Caution**: As with many MCP servers, WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). Project injection could lead to private data exfiltration.

## Prerequisites

- Go 1.19+
- Python 3.6+
- [UV](https://github.com/astral-sh/uv) Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Claude Desktop or Cursor
- FFmpeg (optional) - Only needed for sending audio messages as WhatsApp voice notes

## 5-Minute Quickstart

Get started with SQLite (zero configuration) using the automated startup script:

### 1. Clone and Start

```bash
git clone https://github.com/lharries/whatsapp-mcp.git
cd whatsapp-mcp
./start-mcp.sh start
```

The script will:
- Automatically start the Go bridge on port 8080
- Store data in SQLite (no setup required)
- Display the QR code URL for authentication

### 2. Authenticate with WhatsApp

1. Open http://localhost:8080/qr in your browser
2. Open WhatsApp on your phone → Settings → Linked Devices → Link a Device
3. Scan the QR code from your browser
4. Wait for initial message sync (may take a few minutes)

Check sync status at http://localhost:8080/status

### 3. Connect Claude Desktop or Cursor

**For Claude Desktop**, edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/whatsapp-mcp/whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

**For Cursor**, edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/whatsapp-mcp/whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

**Find your paths:**
```bash
which uv              # Use this path for "command"
cd whatsapp-mcp && pwd    # Use this path + "/whatsapp-mcp-server"
```

### 4. Restart and Start Using

Restart Claude Desktop or Cursor. The WhatsApp integration should now be available.

Try: "Show me my recent WhatsApp messages" or "Send a message to John"

## Client Connection Examples

### Claude Desktop (macOS)

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/Users/yourname/.local/bin/uv",
      "args": ["--directory", "/Users/yourname/whatsapp-mcp/whatsapp-mcp-server", "run", "main.py"]
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/Users/yourname/.local/bin/uv",
      "args": ["--directory", "/Users/yourname/whatsapp-mcp/whatsapp-mcp-server", "run", "main.py"]
    }
  }
}
```

## Configuration Matrix

| Database | Purpose | When to Use | Configuration |
|----------|---------|-------------|---------------|
| **SQLite** (default) | Messages & Sessions | Local development, single user | No config needed |
| **PostgreSQL** | Messages & Sessions | Production, multi-instance | Set `DATABASE_URL` |
| **Supabase** | Messages & Sessions | Managed cloud database | Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY` |

**Quick PostgreSQL Setup:**
```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/path/to/uv",
      "args": ["--directory", "/path/to/whatsapp-mcp-server", "run", "main.py"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@host:5432/dbname"
      }
    }
  }
}
```

For advanced database configurations, session storage options, and migration guides, see [Database Configuration](docs/database.md).

## Documentation

### Core Setup
- **[Database Configuration](docs/database.md)** - PostgreSQL, Supabase, session storage options
- **[Database Migrations](docs/migrations.md)** - Schema setup and data migration
- **[Status Monitoring](docs/status.md)** - Health checks, sync status, web dashboard

### Deployment
- **[Docker Deployment](docs/deployment/docker.md)** - Container setup with Docker Compose
- **[Cloud Run Deployment](docs/deployment/cloud-run.md)** - GCP deployment with OAuth

### Platform-Specific
- **[Windows Setup](docs/platforms/windows.md)** - CGO configuration and troubleshooting
- **[Networking](docs/networking.md)** - Network requirements and firewall configuration

### Troubleshooting
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions

## Architecture

The application consists of two components that work together:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`) - Connects to WhatsApp's API, handles authentication, stores messages in a database
2. **Python MCP Server** (`whatsapp-mcp-server/`) - Provides MCP tools for Claude to interact with WhatsApp data

The Python server automatically manages the Go bridge lifecycle - no manual startup required.

## Available Tools

When connected to Claude, you have access to these WhatsApp capabilities:

**Messaging:**
- `send_message` - Send text messages
- `send_file` - Send images, videos, documents
- `send_audio_message` - Send voice messages

**Search & Read:**
- `search_contacts` - Find contacts by name/number
- `list_messages` - Get message history with filters
- `list_chats` - View all conversations
- `get_chat` - Get chat details
- `download_media` - Download message attachments

**Status:**
- `get_sync_status` - Check connection and sync status
- `check_bridge_status` - Verify bridge health

## Need Help?

- **Getting Started Issues**: See [Troubleshooting Guide](docs/troubleshooting.md)
- **Database Setup**: See [Database Configuration](docs/database.md)
- **Deployment**: See [Docker](docs/deployment/docker.md) or [Cloud Run](docs/deployment/cloud-run.md) guides
- **Windows Users**: See [Windows Setup Guide](docs/platforms/windows.md)
- **Monitor Status**: Visit http://localhost:8080/status when running

## Security Considerations

- All data is stored locally by default (SQLite)
- Messages are only sent to Claude when you explicitly use tools
- For production deployments, see [Cloud Run Security](docs/deployment/cloud-run.md#security-configuration)
- Be aware of [prompt injection risks](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)

## License

MIT
