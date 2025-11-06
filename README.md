# WhatsApp MCP Server

This is a Model Context Protocol (MCP) server for WhatsApp.

With this you can search and read your personal Whatsapp messages (including images, videos, documents, and audio messages), search your contacts and send messages to either individuals or groups. You can also send media files including images, videos, documents, and audio messages.

It connects to your **personal WhatsApp account** directly via the Whatsapp web multidevice API (using the [whatsmeow](https://github.com/tulir/whatsmeow) library). All your messages are stored locally in a SQLite database and only sent to an LLM (such as Claude) when the agent accesses them through tools (which you control).

Here's an example of what you can do when it's connected to Claude.

![WhatsApp MCP](./example-use.png)

> To get updates on this and other projects I work on [enter your email here](https://docs.google.com/forms/d/1rTF9wMBTN0vPfzWuQa2BjfGKdKIpTbyeKxhPMcEzgyI/preview)

> *Caution:* as with many MCP servers, the WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). This means that project injection could lead to private data exfiltration.

## Installation

> **For production deployments on Google Cloud Platform**, see the [GCP Cloud Run Deployment](#deploying-to-google-cloud-platform-gcp) section below.

### Prerequisites

- Go
- Python 3.6+
- Anthropic Claude Desktop app (or Cursor)
- UV (Python package manager), install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- FFmpeg (_optional_) - Only needed for audio messages. If you want to send audio files as playable WhatsApp voice messages, they must be in `.ogg` Opus format. With FFmpeg installed, the MCP server will automatically convert non-Opus audio files. Without FFmpeg, you can still send raw audio files using the `send_file` tool.

### Steps

1. **Clone this repository**

   ```bash
   git clone https://github.com/lharries/whatsapp-mcp.git
   cd whatsapp-mcp
   ```

2. **Authentication Setup**

   The WhatsApp MCP server now features **automatic bridge management**. You have two options:

   **Option A: Manual Bridge Startup (Traditional)**
   Navigate to the whatsapp-bridge directory and run the Go application:

   ```bash
   cd whatsapp-bridge
   go run main.go
   ```

   **Option B: Automatic Startup (Recommended)**
   Skip manual bridge startup! The MCP server will automatically start the bridge when you use any WhatsApp tool in Claude.

   #### Authentication Process
   - **First Time**: You'll need to scan a QR code to authenticate
   - **QR Code Access**: Visit `http://localhost:8080/qr` in your browser to see the QR code
   - **Mobile App**: Open WhatsApp → Settings → Linked Devices → Link a Device → Scan QR code
   - **Re-authentication**: After ~20 days, you may need to re-authenticate using the same process

   #### Bridge Status Monitoring
   - **Status Dashboard**: `http://localhost:8080/status` - Visual dashboard with real-time status
   - **QR Code Page**: `http://localhost:8080/qr` - Authentication QR code when needed
   - **API Status**: `http://localhost:8080/api/status` - JSON status data

3. **Database Configuration (Optional)**

   By default, the server uses SQLite with no configuration required. To use PostgreSQL or Supabase:

   **For local runs (Option A):**
   Set the environment variable before starting the bridge:
   ```bash
   export DATABASE_URL="postgres://username:password@localhost:5432/database_name"
   # Or for Supabase:
   export DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"
   ```

   **For Claude Desktop (Option B):**
   Add the `env` section to your MCP configuration (see step 3 below).

   See the [Database Options](#database-options) section for detailed configuration examples.

4. **Connect to the MCP server**

   Copy the below json with the appropriate {{PATH}} values:

   ```json
   {
     "mcpServers": {
       "whatsapp": {
         "command": "{{PATH_TO_UV}}", // Run `which uv` and place the output here
         "args": [
           "--directory",
           "{{PATH_TO_SRC}}/whatsapp-mcp/whatsapp-mcp-server", // cd into the repo, run `pwd` and enter the output here + "/whatsapp-mcp-server"
           "run",
           "main.py"
         ],
         // Optional: Set DATABASE_URL for PostgreSQL or Supabase
         // "env": {
         //   "DATABASE_URL": "postgres://username:password@localhost:5432/database_name"
         // }
       }
     }
   }
   ```

   For **Claude**, save this as `claude_desktop_config.json` in your Claude Desktop configuration directory at:

   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

   For **Cursor**, save this as `mcp.json` in your Cursor configuration directory at:

   ```
   ~/.cursor/mcp.json
   ```

5. **Restart Claude Desktop / Cursor**

   Open Claude Desktop and you should now see WhatsApp as an available integration.

   Or restart Cursor.

### Windows Compatibility

If you're running this project on Windows, be aware that `go-sqlite3` requires **CGO to be enabled** in order to compile and work properly. By default, **CGO is disabled on Windows**, so you need to explicitly enable it and have a C compiler installed.

#### Steps to get it working:

1. **Install a C compiler**  
   We recommend using [MSYS2](https://www.msys2.org/) to install a C compiler for Windows. After installing MSYS2, make sure to add the `ucrt64\bin` folder to your `PATH`.  
   → A step-by-step guide is available [here](https://code.visualstudio.com/docs/cpp/config-mingw).

2. **Enable CGO and run the app**

   ```bash
   cd whatsapp-bridge
   go env -w CGO_ENABLED=1
   go run main.go
   ```

Without this setup, you'll likely run into errors like:

> `Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work.`

## Architecture Overview

This application consists of two main components:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): A Go application that connects to WhatsApp's web API, handles authentication via QR code, and stores message history in SQLite. It serves as the bridge between WhatsApp and the MCP server.

2. **Python MCP Server** (`whatsapp-mcp-server/`): A Python server implementing the Model Context Protocol (MCP), which provides standardized tools for Claude to interact with WhatsApp data and send/receive messages.

### Data Storage

- All message history is stored in a database (SQLite by default, PostgreSQL supported)
- The database maintains tables for chats and messages
- Messages are indexed for efficient searching and retrieval

### Database Options

The WhatsApp MCP server supports multiple database backends through the `DATABASE_URL` environment variable:

#### SQLite (Default)

SQLite is the default option and requires no configuration. Data is stored locally in the `whatsapp-bridge/store/` directory.

**Format:**
```bash
# No configuration needed - uses SQLite by default
# Or explicitly set:
DATABASE_URL="file:store/messages.db?_foreign_keys=on"
```

**Advantages:**
- Zero configuration required
- No external database server needed
- Fast for local development
- Portable database files

#### PostgreSQL

Use PostgreSQL for production deployments, shared environments, or Supabase integration.

**Format:**
```bash
# Local PostgreSQL
DATABASE_URL="postgres://username:password@localhost:5432/database_name"

# PostgreSQL with SSL (production)
DATABASE_URL="postgresql://username:password@host:5432/database_name?sslmode=require"
```

**Advantages:**
- Better for production deployments
- Supports concurrent access from multiple instances
- Advanced querying and performance features
- Cloud-hosted options available (Supabase, AWS RDS, etc.)

#### Supabase

Supabase provides a managed PostgreSQL database with additional features.

**Format:**
```bash
DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"
```

**Setup:**
1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Find your connection string in Settings → Database
3. Set the `DATABASE_URL` environment variable
4. The schema will be created automatically on first run

**Advantages:**
- Managed PostgreSQL service
- Automatic backups and scaling
- Built-in authentication and storage
- Free tier available

#### Configuration Matrix

The WhatsApp MCP server supports independent configuration of two database concerns:

| Database Type | Purpose | Environment Variable | Default |
|---------------|---------|---------------------|---------|
| **Messages** | Chat history, message content, media metadata | `DATABASE_URL` | SQLite: `file:store/messages.db` |
| **Sessions** | WhatsApp authentication, device keys, contacts | `WHATSAPP_SESSION_DATABASE_URL` | Falls back to `DATABASE_URL`, then SQLite: `file:store/whatsapp.db` |

**Supported Combinations:**

| Messages DB | Session DB | Use Case | Configuration |
|-------------|------------|----------|---------------|
| SQLite | SQLite | Default local development | No configuration needed |
| PostgreSQL/Supabase | PostgreSQL/Supabase (same) | Production with shared database | Set `DATABASE_URL` only |
| PostgreSQL/Supabase | PostgreSQL/Supabase (separate) | Production with isolated databases | Set both `DATABASE_URL` and `WHATSAPP_SESSION_DATABASE_URL` |
| SQLite | PostgreSQL/Supabase | Local messages, remote sessions | Set `WHATSAPP_SESSION_DATABASE_URL` only |
| PostgreSQL/Supabase | SQLite | Remote messages, local sessions | Set `DATABASE_URL` only |

**Environment Variable Precedence:**

```bash
# Messages database (used by Python MCP server and Go bridge)
DATABASE_URL → defaults to SQLite: file:store/messages.db

# Session database (used only by Go bridge for whatsmeow session storage)
WHATSAPP_SESSION_DATABASE_URL → falls back to DATABASE_URL → defaults to SQLite: file:store/whatsapp.db
```

**Example Configurations:**

```bash
# Local development (default)
# No configuration needed - uses SQLite for both

# Production: All data in Supabase
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
export SUPABASE_URL="https://[PROJECT].supabase.co"
export SUPABASE_KEY="[SERVICE-KEY]"

# Production: Separate Supabase databases for messages and sessions
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
export WHATSAPP_SESSION_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
export SUPABASE_URL="https://[PROJECT].supabase.co"
export SUPABASE_KEY="[SERVICE-KEY]"

# Hybrid: Local sessions, remote messages
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
# WHATSAPP_SESSION_DATABASE_URL not set, uses local SQLite
```

#### Schema Management

**Database Schema Setup:**

The database schema must be pre-created before running the bridge. The bridge requires two core tables: `chats` and `messages`.

**Required Tables:**

1. **chats** table:
   - `jid` (TEXT PRIMARY KEY): Chat identifier
   - `name` (TEXT): Chat display name
   - `last_message_time` (TIMESTAMP): Timestamp of most recent message

2. **messages** table:
   - `id` (TEXT): Message identifier
   - `chat_jid` (TEXT): Foreign key to chats(jid)
   - `sender` (TEXT): Message sender identifier
   - `content` (TEXT): Message content
   - `timestamp` (TIMESTAMP): Message timestamp
   - `is_from_me` (BOOLEAN): Whether message is from authenticated user
   - `media_type` (TEXT NULL): Type of media if applicable
   - `filename` (TEXT NULL): Media filename if applicable
   - `url` (TEXT NULL): Media URL if applicable
   - `media_key` (BLOB/BYTEA NULL): Encryption key for media
   - `file_sha256` (BLOB/BYTEA NULL): File hash
   - `file_enc_sha256` (BLOB/BYTEA NULL): Encrypted file hash
   - `file_length` (INTEGER/BIGINT NULL): File size in bytes
   - PRIMARY KEY: (id, chat_jid)

**Applying Migrations:**

Run the base schema migration before starting the bridge:

```bash
# For SQLite
sqlite3 store/messages.db < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For PostgreSQL
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

For Cloud SQL deployments, see `gcp/DATABASE_SETUP.md` for detailed setup instructions.

**Type Mapping:**
| SQLite Type | PostgreSQL Type | Usage |
|-------------|-----------------|-------|
| `BLOB` | `BYTEA` | Media keys, file hashes |
| `INTEGER` | `BIGINT` | File sizes, IDs |
| `TEXT` | `TEXT` | Messages, names, JIDs |
| `TIMESTAMP` | `TIMESTAMP` | Message times |
| `BOOLEAN` | `BOOLEAN` | Flags (is_from_me) |

**Required Tables:**

The following tables must exist before running the bridge:

1. **chats**
   - Columns: `jid` (TEXT PRIMARY KEY), `name` (TEXT), `last_message_time` (TIMESTAMP)
   - Purpose: Stores chat/group metadata

2. **messages**
   - Columns:
     - `id` (TEXT, part of primary key)
     - `chat_jid` (TEXT, part of primary key, foreign key to chats.jid)
     - `sender` (TEXT)
     - `content` (TEXT)
     - `timestamp` (TIMESTAMP)
     - `is_from_me` (BOOLEAN)
     - `media_type` (TEXT, nullable)
     - `filename` (TEXT, nullable)
     - `url` (TEXT, nullable)
     - `media_key` (BLOB for SQLite, BYTEA for PostgreSQL, nullable)
     - `file_sha256` (BLOB for SQLite, BYTEA for PostgreSQL, nullable)
     - `file_enc_sha256` (BLOB for SQLite, BYTEA for PostgreSQL, nullable)
     - `file_length` (INTEGER for SQLite, BIGINT for PostgreSQL, nullable)
   - Primary Key: (id, chat_jid)
   - Purpose: Stores message history and media metadata

**Quick Migration Commands:**

```bash
# For SQLite (local development)
sqlite3 store/messages.db < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For PostgreSQL (production/cloud)
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For Cloud SQL (see gcp/DATABASE_SETUP.md for details)
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

See `gcp/DATABASE_SETUP.md` for detailed Cloud SQL setup instructions.

**Migration from SQLite to PostgreSQL:**
1. Export your SQLite data (if needed)
2. Set `DATABASE_URL` to your PostgreSQL connection string
3. Restart the bridge - schema will be created automatically
4. Import data (if migrating existing messages)

Note: The bridge does not automatically migrate data between database types. If you have existing data in SQLite that you want to preserve, you'll need to export and import it manually.

#### Storing WhatsApp Sessions in Supabase

**Overview**

By default, WhatsApp session data (authentication, device keys, contacts) is stored in local SQLite files. For production deployments, you can store sessions in Supabase Postgres for better persistence, backup, and multi-instance support.

**Step 1: Run Session Tables Migration**

The Go bridge requires specific tables created by `go.mau.fi/whatsmeow/store/sqlstore`. Run the migration:

```bash
# Option A: Using Supabase SQL Editor (Recommended)
# 1. Go to your Supabase project dashboard
# 2. Navigate to SQL Editor
# 3. Copy contents of whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
# 4. Paste and execute

# Option B: Using psql
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres" \
  -f whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
```

This creates 13 tables: `devices`, `identities`, `prekeys`, `sessions`, `sender_keys`, `signed_prekeys`, `app_state_sync_keys`, `app_state_version`, `app_state_mutation_macs`, `contacts`, `chat_settings`, `message_secrets`, `privacy_tokens`.

**Step 2: Verify Tables**

```sql
-- Check devices table exists
SELECT to_regclass('public.devices');
-- Should return: "devices"

-- Verify all 13 session tables exist
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('devices', 'identities', 'prekeys', 'sessions', 'sender_keys',
                  'signed_prekeys', 'app_state_sync_keys', 'app_state_version',
                  'app_state_mutation_macs', 'contacts', 'chat_settings',
                  'message_secrets', 'privacy_tokens');
-- Should return 13 rows
```

**Step 3: Configure Session DSN**

Set the `WHATSAPP_SESSION_DATABASE_URL` environment variable with your Supabase Postgres connection string:

```bash
# Format (ensure sslmode=require for Supabase)
export WHATSAPP_SESSION_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require"
```

**Important:** Use your Supabase **service key** (not anon key) for the Python MCP server, as the session tables have RLS enabled with deny-all policies.

**Step 4: Deploy with Session DSN**

**For Docker Compose:**
```yaml
environment:
  - WHATSAPP_SESSION_DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require
```

**For Cloud Run (via Secret Manager):**
```bash
# Create secret
gcloud secrets create whatsapp-mcp-session-dsn \
  --data-file=- <<EOF
postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require
EOF

# Grant access
gcloud secrets add-iam-policy-binding whatsapp-mcp-session-dsn \
  --member="serviceAccount:[SERVICE-ACCOUNT]@[PROJECT].iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Reference in cloudrun.yaml (uncomment):
# - name: WHATSAPP_SESSION_DATABASE_URL
#   valueFrom:
#     secretKeyRef:
#       name: whatsapp-mcp-session-dsn
#       key: latest
```

**For Terraform:**

Terraform configuration already includes the `session_dsn` secret resource. Update the value:

```bash
# After applying terraform
gcloud secrets versions add whatsapp-mcp-session-dsn \
  --data-file=- <<EOF
postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require
EOF
```

**Step 5: Verify**

Check the bridge logs and session backend status:

```bash
# Bridge logs should show:
# "Using Postgres session store"
# "Postgres session DSN host: db.[PROJECT].supabase.co"
# "✓ Session tables validated successfully"

# Check via API:
curl http://localhost:8080/api/session-backend
# Response should include:
# "backend": "postgres"
# "session_tables_ok": true
# "session_host": "db.[PROJECT].supabase.co"
```

**Security Notes:**

- Session tables have Row Level Security (RLS) enabled with deny-all policies by default
- Only `service_role` can access session tables (anon/authenticated roles cannot)
- The Go bridge connects directly and bypasses RLS
- Client-side Supabase SDKs must never access session tables
- Store the service key in Secret Manager, not in environment variables

**GCS Backup Behavior:**

GCS session backup (`GCS_SESSION_BUCKET`) only works with SQLite sessions. If using Postgres/Supabase for sessions:
- GCS upload/download is automatically skipped
- Use Supabase's built-in backups or `pg_dump` for session backup
- Bridge logs will indicate "GCS session backup is only for SQLite, skipping"

**Troubleshooting:**

```bash
# If bridge fails to start:
# 1. Check migration was applied
SELECT to_regclass('public.devices');

# 2. Check connection string includes sslmode
echo $WHATSAPP_SESSION_DATABASE_URL | grep sslmode=require

# 3. Check RLS permissions
SELECT grantee, privilege_type FROM information_schema.table_privileges
WHERE table_name = 'devices';
# Should show service_role has SELECT, INSERT, UPDATE, DELETE

# 4. Test connection
psql "$WHATSAPP_SESSION_DATABASE_URL" -c "SELECT 1"
```

For complete migration documentation, see `whatsapp-mcp-server/migrations/README.md`.

#### Docker Database Configuration

When using Docker Compose, you can enable PostgreSQL by uncommenting the relevant sections in `docker-compose.yml`:

**Enable PostgreSQL Service:**
```yaml
# Uncomment the postgres service
postgres:
  image: postgres:15-alpine
  container_name: whatsapp-postgres
  # ... (see docker-compose.yml)
```

**Configure Environment Variables:**
```yaml
environment:
  # Uncomment and set DATABASE_URL
  - DATABASE_URL=postgres://whatsapp:whatsapp_password@postgres:5432/whatsapp?sslmode=disable
```

**Enable Dependency:**
```yaml
# Uncomment depends_on
depends_on:
  postgres:
    condition: service_healthy
```

See the [Running in Docker](#running-in-docker) section for complete Docker configuration details.

## Usage

Once connected, you can interact with your WhatsApp contacts through Claude, leveraging Claude's AI capabilities in your WhatsApp conversations.

### MCP Tools

Claude can access the following tools to interact with WhatsApp:

#### Message and Chat Management
- **search_contacts**: Search for contacts by name or phone number
- **list_messages**: Retrieve messages with optional filters and context
- **list_chats**: List available chats with metadata
- **get_chat**: Get information about a specific chat
- **get_direct_chat_by_contact**: Find a direct chat with a specific contact
- **get_contact_chats**: List all chats involving a specific contact
- **get_last_interaction**: Get the most recent message with a contact
- **get_message_context**: Retrieve context around a specific message

#### Message Sending
- **send_message**: Send a WhatsApp message to a specified phone number or group JID
- **send_file**: Send a file (image, video, raw audio, document) to a specified recipient
- **send_audio_message**: Send an audio file as a WhatsApp voice message (requires the file to be an .ogg opus file or ffmpeg must be installed)

#### Media Management
- **download_media**: Download media from a WhatsApp message and get the local file path

#### Status Monitoring
- **get_sync_status**: Get comprehensive sync status including bridge health, database statistics, and last sync time
- **check_bridge_status**: Check the current status of the WhatsApp bridge and authentication

### MCP Resources

Claude can also access these resources for status information:

- **whatsapp://sync-status**: JSON resource providing real-time bridge and sync status
- **whatsapp://status-ui**: Rich HTML status display with visual indicators and statistics

### Media Handling Features

The MCP server supports both sending and receiving various media types:

#### Media Sending

You can send various media types to your WhatsApp contacts:

- **Images, Videos, Documents**: Use the `send_file` tool to share any supported media type.
- **Voice Messages**: Use the `send_audio_message` tool to send audio files as playable WhatsApp voice messages.
  - For optimal compatibility, audio files should be in `.ogg` Opus format.
  - With FFmpeg installed, the system will automatically convert other audio formats (MP3, WAV, etc.) to the required format.
  - Without FFmpeg, you can still send raw audio files using the `send_file` tool, but they won't appear as playable voice messages.

#### Media Downloading

By default, just the metadata of the media is stored in the local database. The message will indicate that media was sent. To access this media you need to use the download_media tool which takes the `message_id` and `chat_jid` (which are shown when printing messages containing the meda), this downloads the media and then returns the file path which can be then opened or passed to another tool.

### Status Monitoring Features

The WhatsApp MCP server includes comprehensive status monitoring capabilities:

#### Web Dashboard
Access a visual status dashboard at `http://localhost:8080/status` when the bridge is running:
- Real-time bridge and authentication status
- Database statistics (message count, chat count, database size)
- Last sync timestamp
- Auto-refresh every 30 seconds
- Visual status indicators with color-coded badges

#### MCP Status Tools
- **Bridge Health**: Check if the WhatsApp bridge process is running and responsive
- **Authentication Status**: Monitor WhatsApp authentication state and QR code availability
- **Sync Statistics**: View message counts, chat counts, and database metrics
- **Error Reporting**: Get detailed error messages and troubleshooting guidance

#### Automatic Bridge Management
- **Auto-startup**: All MCP tools automatically start the bridge if it's not running
- **Health Monitoring**: Continuous monitoring of bridge process and API responsiveness
- **Authentication Recovery**: Automatic QR code generation for re-authentication

#### Status Access Methods
1. **MCP Tools**: Call `get_sync_status` or `check_bridge_status` in Claude
2. **MCP Resources**: View `whatsapp://sync-status` or `whatsapp://status-ui` resources
3. **Web Interface**: Visit `http://localhost:8080/status` in your browser
4. **API Endpoint**: Access `http://localhost:8080/api/status` for JSON data

## Technical Details

1. Claude sends requests to the Python MCP server
2. The MCP server queries the Go bridge for WhatsApp data or directly to the SQLite database
3. The Go accesses the WhatsApp API and keeps the SQLite database up to date
4. Data flows back through the chain to Claude
5. When sending messages, the request flows from Claude through the MCP server to the Go bridge and to WhatsApp

## Troubleshooting

### General Issues
- If you encounter permission issues when running uv, you may need to add it to your PATH or use the full path to the executable.
- With automatic bridge management, you only need the Python MCP server running - the Go bridge will start automatically.

### Bridge and Connection Issues

#### Bridge Startup Problems
- **Auto-startup Fails**: Check the status dashboard at `http://localhost:8080/status` for detailed error information
- **Go Not Found**: Ensure Go is installed and available in PATH (`which go` should return a path)
- **Port Already in Use**: If port 8080 is busy, kill any existing processes: `pkill -f 'go run main.go'`
- **Permission Issues**: Ensure the MCP server has permission to start the Go bridge process

#### Status Monitoring
- **Check Bridge Status**: Use the `check_bridge_status` MCP tool in Claude for real-time diagnostics
- **Web Dashboard**: Visit `http://localhost:8080/status` for visual status monitoring
- **API Diagnostics**: Access `http://localhost:8080/api/status` for JSON status data

### Authentication Issues

- **QR Code Not Displaying**: 
  - Visit `http://localhost:8080/qr` in your browser instead of checking the terminal
  - If the page shows "no QR code available", restart the bridge or use a WhatsApp tool to trigger authentication
- **QR Code Expired**: Refresh the QR code page or restart the bridge to generate a new QR code
- **WhatsApp Already Logged In**: If your session is already active, the bridge will automatically reconnect without showing a QR code
- **Device Limit Reached**: WhatsApp limits linked devices. Remove an existing device: WhatsApp → Settings → Linked Devices
- **Authentication Timeout**: Try using the `check_bridge_status` tool which will attempt to restart the authentication process

### Data Sync Issues

- **No Messages Loading**: After initial authentication, it can take several minutes for message history to load
- **Missing Recent Messages**: The bridge syncs incrementally; recent messages should appear within a few seconds
- **WhatsApp Out of Sync**: Delete both database files and restart:
  ```bash
  rm whatsapp-bridge/store/messages.db whatsapp-bridge/store/whatsapp.db
  # Bridge will restart automatically when you use a WhatsApp tool
  ```

### Status Dashboard Issues

- **Dashboard Not Loading**: Ensure the bridge is running by calling a WhatsApp MCP tool first
- **Status Shows "Not Ready"**: Check individual status indicators for specific issues
- **Auto-refresh Not Working**: Browser may have JavaScript disabled; manually refresh the page

For additional Claude Desktop integration troubleshooting, see the [MCP documentation](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues). The documentation includes helpful tips for checking logs and resolving common issues.

## Running in Docker

The WhatsApp MCP server supports containerized deployment using Docker and Docker Compose. The container includes both the Go bridge and Python MCP server in a single, optimized image that preserves all automatic bridge management features.

### Quick Start

1. **Build and start the container:**
   ```bash
   docker-compose up -d
   ```

2. **Access the QR code for authentication:**
   - Web interface: `http://localhost:8080/qr`
   - Status dashboard: `http://localhost:8080/status`

3. **Configure Claude Desktop** to use the containerized MCP server (see configuration below)

### Architecture

The Docker deployment uses a **combined container approach** that includes:
- **Go Bridge**: Compiled binary handling WhatsApp API communication
- **Go Runtime**: Available for automatic bridge process management
- **Python MCP Server**: Full MCP functionality with automatic bridge management
- **Shared Storage**: SQLite databases persisted via Docker volumes

This architecture ensures that all automatic bridge management features (startup, monitoring, QR code capture) work exactly as in local installations.

### MCP Transport Modes

The MCP server supports two transport modes, configurable via the `MCP_TRANSPORT` environment variable:

#### **STDIO Transport** (Default for local installations)
- **Use case:** Local development, direct MCP client connections
- **Characteristics:** 
  - Communication via standard input/output streams
  - Lower latency for local connections
  - Requires direct process management
- **Claude Configuration:**
  ```json
  {
    "mcpServers": {
      "whatsapp": {
        "command": "uv",
        "args": ["run", "main.py"],
        "cwd": "/path/to/whatsapp-mcp-server"
      }
    }
  }
  ```

#### **SSE Transport** (Default for Docker)
- **Use case:** Containerized deployments, web-based integrations
- **Characteristics:**
  - Communication via HTTP Server-Sent Events
  - Better suited for container environments
  - Enables web-based MCP client connections
  - Listens on port 3000 by default
- **Claude Configuration:**
  ```json
  {
    "mcpServers": {
      "whatsapp": {
        "command": "docker",
        "args": [
          "exec",
          "-i",
          "whatsapp-mcp-server",
          "uv",
          "run",
          "main.py"
        ]
      }
    }
  }
  ```

### Environment Variables

Configure the Docker deployment using these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `sse` (Docker), `stdio` (local) | MCP transport protocol |
| `WHATSAPP_BRIDGE_URL` | `http://localhost:8080` | Bridge API endpoint (localhost in combined container) |
| `DATABASE_PATH` | `/app/whatsapp-bridge/store/messages.db` | SQLite database path |
| `WHATSAPP_DB_PATH` | `/app/whatsapp-bridge/store` | Bridge database directory |

### Docker Compose Configuration

The provided `docker-compose.yml` includes:

- **Combined Container**: Single container with both Go bridge and Python MCP server
- **Automatic Bridge Management**: Full subprocess control and monitoring within container
- **Persistent Storage**: SQLite databases stored in Docker volume
- **Health Checks**: Container health monitoring via bridge API
- **Port Mapping**: Web interface (8080) and MCP server (3000)

### Customizing Transport Mode

To override the default SSE transport in Docker:

```bash
# Use STDIO transport in Docker (not recommended)
MCP_TRANSPORT=stdio docker-compose up

# Or set in docker-compose.yml
environment:
  - MCP_TRANSPORT=stdio
```

To use SSE transport locally:

```bash
# Set environment variable
export MCP_TRANSPORT=sse
uv run main.py
```

### Transport Mode Implications

| Aspect | STDIO | SSE |
|--------|-------|-----|
| **Latency** | Lower | Slightly higher |
| **Docker Support** | Limited | Excellent |
| **Web Integration** | Not suitable | Native support |
| **Process Management** | Direct | Via HTTP |
| **Debugging** | Terminal logs | HTTP logs + browser tools |
| **Scalability** | Single instance | Multiple clients possible |

### Recommended Configurations

- **Local Development**: Use STDIO transport with direct Python execution
- **Production Docker**: Use SSE transport with Docker Compose
- **CI/CD Pipelines**: Use Docker with SSE transport for testing
- **Development Docker**: Use SSE transport for consistency with production

## Deploying to Google Cloud Platform (GCP)

The WhatsApp MCP server can be deployed to Google Cloud Platform using Cloud Run for serverless, auto-scaling infrastructure with OAuth 2.1 authentication. This deployment includes:

- **Cloud Run**: Containerized MCP server with automatic scaling and OAuth protection
- **Supabase**: Managed PostgreSQL database via REST API for message storage (optional)
- **Cloud Storage**: GCS bucket for WhatsApp session persistence and backup
- **Secret Manager**: Secure storage for OAuth credentials and database configuration
- **Identity Platform**: OAuth 2.1 authentication for secure remote client access

**Note**: The current implementation uses SQLite by default or Supabase REST API for database access. Direct PostgreSQL/Cloud SQL connectivity is not currently supported.

### Authentication Overview

The WhatsApp MCP server uses OAuth 2.1 for secure client authentication when deployed remotely:

1. **Authentication Flow:**
   - Client obtains Bearer token from Google Identity Platform
   - Token included in Authorization header with each request
   - Server validates JWT token signature and claims
   - Only authorized clients can access the MCP server

2. **Security Benefits:**
   - Modern OAuth 2.1 protocol with enhanced security
   - JWT-based token validation with audience checking
   - Automatic token expiration and rotation
   - Secure client credentials storage in Secret Manager
   - Token-based access control for multi-user deployments

3. **Client Configuration:**
   - Web-based OAuth consent flow for browser clients
   - Service account authentication for automated tools
   - Fine-grained access control with custom claims
   - Support for organizational and public clients

### Prerequisites

1. **Google Cloud SDK:**
   ```bash
   # Install Google Cloud SDK
   brew install google-cloud-sdk   # macOS
   
   # Configure SDK
   gcloud init
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Required APIs:**
   ```bash
   # Enable necessary APIs
   gcloud services enable \
     run.googleapis.com \
     secretmanager.googleapis.com \
     storage.googleapis.com \
     iamcredentials.googleapis.com \
     identitytoolkit.googleapis.com
   ```

3. **Development Tools:**
   - Docker Desktop (for building container images)
   - Terraform (optional, for infrastructure as code)
   - Cloud SQL Proxy (for local database access)

### OAuth 2.1 Setup

Before deploying the server, set up OAuth 2.1 authentication:

1. **Configure OAuth Consent Screen:**
   ```bash
   # Open OAuth consent screen configuration
   open "https://console.cloud.google.com/apis/credentials/consent"
   
   # Configure settings:
   # - User Type: Internal (recommended) or External
   # - App Name: "WhatsApp MCP Server"
   # - Support Email: Your team's email
   # - Developer Contact: Your team's email
   ```

2. **Create OAuth Credentials:**
   ```bash
   # Create OAuth 2.0 Client ID
   open "https://console.cloud.google.com/apis/credentials"
   
   # Click "Create Credentials" → "OAuth 2.0 Client ID"
   # Choose application type based on your client:
   # - Web Application: For browser-based clients
   # - Desktop Application: For CLI tools
   ```

3. **Store Credentials in Secret Manager:**
   ```bash
   # Store OAuth Client ID
   echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
     gcloud secrets create whatsapp-mcp-google-client-id \
     --replication-policy="automatic" \
     --data-file=-

   # Store OAuth Audience (should match your Google OAuth Client ID)
   # For Google ID tokens, the audience claim equals the OAuth Client ID
   echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
     gcloud secrets create whatsapp-mcp-oauth-audience \
     --replication-policy="automatic" \
     --data-file=-
   ```

### Quick Start with Automated Setup

Deploy the server with automated infrastructure setup:

```bash
# Set project ID and OAuth configuration
export GCP_PROJECT_ID=your-project-id
export OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
# OAUTH_AUDIENCE should match the Google OAuth Client ID for Google ID tokens
export OAUTH_AUDIENCE=your-client-id.apps.googleusercontent.com

# Run automated setup with OAuth configuration
./gcp/setup.sh
```

This script will:
1. Enable required APIs (including Identity Platform)
2. Create a service account with OAuth and storage permissions
3. Create a GCS bucket for session storage
4. Configure OAuth credentials and secrets
5. Display deployment instructions

**Note**: If you need PostgreSQL, set up a Supabase project and configure `SUPABASE_URL` and `SUPABASE_KEY` secrets.

### Alternative: Terraform Deployment

For infrastructure as code with OAuth configuration:

```bash
# Navigate to Terraform directory
cd gcp/terraform

# Configure OAuth and project settings
cat > terraform.tfvars <<EOF
project_id = "your-project-id"
oauth_client_id = "your-client-id.apps.googleusercontent.com"
# OAuth audience should match the Client ID for Google ID tokens
oauth_audience = "your-client-id.apps.googleusercontent.com"
EOF

# Deploy infrastructure
terraform init
terraform plan
terraform apply
```

### Build and Deploy to Cloud Run

Deploy the server with OAuth authentication enabled:

```bash
# Build and push container image using Artifact Registry
gcloud builds submit --tag us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest

# Deploy to Cloud Run with OAuth configuration
gcloud run deploy whatsapp-mcp \
  --image=us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest \
  --region=us-central1 \
  --platform=managed \
  --service-account=whatsapp-mcp-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --update-secrets=\
GOOGLE_CLIENT_ID=whatsapp-mcp-google-client-id:latest,\
OAUTH_AUDIENCE=whatsapp-mcp-oauth-audience:latest \
  --set-env-vars=\
MCP_TRANSPORT=sse,\
MCP_PORT=8000,\
WHATSAPP_BRIDGE_URL=http://localhost:8080,\
GCS_SESSION_BUCKET=${GCP_PROJECT_ID}-whatsapp-sessions,\
GCS_SESSION_OBJECT_NAME=whatsapp.db,\
OAUTH_ENABLED=true

# Optional: Add Supabase secrets if using Supabase for database
# --update-secrets=SUPABASE_URL=whatsapp-mcp-supabase-url:latest,SUPABASE_KEY=whatsapp-mcp-supabase-key:latest

### Database and OAuth Setup

1. **Database Configuration:**

   The server uses SQLite by default (no configuration needed). For Supabase PostgreSQL:

   ```bash
   # Create Supabase project at https://supabase.com
   # Get your project URL and keys from Settings → API

   # Store Supabase credentials in Secret Manager
   echo -n "https://xxxxx.supabase.co" | \
     gcloud secrets create whatsapp-mcp-supabase-url \
     --replication-policy="automatic" \
     --data-file=-

   echo -n "your-supabase-anon-or-service-role-key" | \
     gcloud secrets create whatsapp-mcp-supabase-key \
     --replication-policy="automatic" \
     --data-file=-
   ```

2. **OAuth Client Configuration:**
   ```bash
   # Obtain a Google ID token for your OAuth Client ID
   # The token's audience claim must match your GOOGLE_CLIENT_ID
   # For testing, you can use gcloud to generate a token:
   gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com

   # Test OAuth configuration with /health endpoint (no auth required)
   curl "https://YOUR-SERVICE-URL/health"

   # Should return HTTP 200 OK
   ```

3. **Validate Deployment:**
   ```bash
   # Check service and OAuth status
   gcloud run services describe whatsapp-mcp-server \
     --region=us-central1 \
     --format="yaml(status,metadata.annotations)"
   ```

### Security Configuration

#### IAM Roles and Permissions

Configure minimal required IAM roles for the Cloud Run service account:

```bash
# Required: Secret Manager access
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:whatsapp-mcp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Required: Storage access (grant at bucket level, not project)
gcloud storage buckets add-iam-policy-binding \
  gs://PROJECT_ID-whatsapp-sessions \
  --member="serviceAccount:whatsapp-mcp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

**Important**: Avoid granting project-level Editor or Owner roles.

#### OAuth 2.1 Settings

1. **Token Management:**
   - Use short-lived tokens (1 hour expiry)
   - Implement automatic token refresh
   - Never commit tokens to version control
   - Monitor OAuth usage in audit logs

2. **Client Security:**
   - Use separate client IDs for dev/staging/prod
   - Configure appropriate scopes and permissions
   - Implement token validation on client side
   - Store credentials in Secret Manager only

3. **Server Security:**
   - Enable OAuth for all endpoints except /health
   - Configure audience validation (Client ID)
   - Set up CORS for allowed origins if needed

#### Secrets Management

1. **Rotation cadence:**
   - OAuth credentials: Every 90 days
   - Supabase keys: Every 180 days
   - Immediate rotation on security incidents

2. **Audit logging:**
   ```bash
   # Enable Data Access logs for Secret Manager
   # Console: IAM & Admin → Audit Logs → Secret Manager
   # Enable: Admin Read, Data Read, Data Write

   # Monitor secret access
   gcloud logging read \
     "resource.type=secretmanager.googleapis.com/Secret" \
     --limit=50
   ```

3. **Access control:**
   - Grant secretAccessor role only to required service accounts
   - Use separate secrets per environment
   - Enable automatic secret versioning

#### Network Security

1. **Ingress controls:**
   ```bash
   # Restrict Cloud Run ingress
   gcloud run services update whatsapp-mcp \
     --ingress=internal-and-cloud-load-balancing
   ```

2. **VPC Service Controls** (optional):
   - Create service perimeter for Secret Manager
   - Restrict data exfiltration
   - Requires organization-level VPC-SC setup

3. **Cloud Armor** (optional):
   - Deploy Cloud Load Balancer
   - Configure rate limiting and DDoS protection
   - Implement geo-blocking if needed

### GCP Documentation

Complete documentation is available in the `gcp/` directory:

- **[gcp/API_REQUIREMENTS.md](gcp/API_REQUIREMENTS.md)**: Required GCP APIs including Identity Platform
- **[gcp/OAUTH_SETUP.md](gcp/OAUTH_SETUP.md)**: Detailed OAuth 2.1 configuration guide
- **[gcp/README.md](gcp/README.md)**: Cloud Run deployment guide
- **[gcp/env-template.yaml](gcp/env-template.yaml)**: Environment variables reference
- **[gcp/setup.sh](gcp/setup.sh)**: Automated provisioning script
- **[gcp/terraform/](gcp/terraform/)**: Infrastructure as code

### Monitoring and Management

1. **Service Monitoring:**
   ```bash
   # View service logs with OAuth events
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp AND jsonPayload.oauth=*" --limit=50

   # Monitor OAuth token usage
   gcloud run services describe whatsapp-mcp \
     --region=us-central1 \
     --format="yaml(status.traffic,status.conditions)"
   ```

2. **Management Consoles:**
   - **Cloud Run**: [Service Dashboard](https://console.cloud.google.com/run)
   - **OAuth**: [Credentials](https://console.cloud.google.com/apis/credentials)
   - **Cloud SQL**: [Database](https://console.cloud.google.com/sql)
   - **Secret Manager**: [Secrets](https://console.cloud.google.com/security/secret-manager)
   - **Storage**: [GCS Buckets](https://console.cloud.google.com/storage)

3. **OAuth Usage Stats:**
   - Token issuance metrics
   - Active client tracking
   - Authentication failures
   - Token revocations

### Cost Considerations

Monthly cost estimates for running WhatsApp MCP on GCP:

#### Development Environment
- **Cloud Run**: Free tier (2M requests/month) - ~$0
- **Cloud Storage**: 5GB free tier - ~$0
- **Secret Manager**: 6 secrets, free tier - ~$0
- **Total**: ~$0-5/month (if within free tiers)

#### Production Environment (Low Traffic)
- **Cloud Run**: Min instances=0, ~100K requests/month - ~$0-10
- **Cloud Storage**: 10GB session data - ~$0.20
- **Secret Manager**: 6 secrets - ~$0.06
- **Supabase** (optional): Free tier or ~$25/month for Pro
- **Total**: ~$0-35/month

#### Production Environment (High Availability)
- **Cloud Run**: Min instances=1, ~1M requests/month - ~$50-100
- **Cloud Storage**: 50GB session data + backups - ~$1
- **Secret Manager**: 10 secrets with rotation - ~$0.10
- **Supabase Pro**: ~$25/month
- **Total**: ~$75-125/month

#### Cost Optimization Tips:
- Use min-instances=0 for development
- Implement request caching to reduce Cloud Run costs
- Use GCS lifecycle policies to archive old session data
- Monitor usage with Cost Alerts and Budgets
- Leverage free tiers for small deployments

### Troubleshooting

1. **OAuth Issues:**
   - **Invalid Token**: Check audience and issuer claims
   - **Token Expired**: Verify token lifetime settings
   - **Missing Claims**: Review OAuth consent screen
   - **CORS Errors**: Check allowed origins

2. **Infrastructure:**
   - **API Not Enabled**: Run setup script or enable manually
   - **Storage Access**: Check GCS bucket permissions
   - **Secrets**: Verify Secret Manager access
   - **Container**: Validate build and dependencies
   - **Supabase Connection**: Verify URL and key if using Supabase

3. **Common Fixes:**
   ```bash
   # Test health endpoint (should bypass OAuth)
   curl -v "https://YOUR-SERVICE-URL/health"  # Should return 200 OK

   # Obtain a Google ID token with correct audience for testing
   TOKEN=$(gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com)

   # Check service account permissions
   gcloud projects get-iam-policy ${GCP_PROJECT_ID} \
     --flatten="bindings[].members" \
     --filter="bindings.members:whatsapp-mcp-sa"

   # View service logs for OAuth errors
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp" --limit=50
   ```

### Remote MCP Client Configuration

Once deployed to Cloud Run, configure your MCP clients (Claude Desktop or Cursor) to connect to the remote server:

#### Claude Desktop Configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "whatsapp-remote": {
      "transport": "sse",
      "url": "https://whatsapp-mcp-xxxxx-uc.a.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_GOOGLE_ID_TOKEN"
      }
    }
  }
}
```

#### Cursor Configuration

Edit `~/.cursor/mcp.json` (macOS/Linux) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "whatsapp-remote": {
      "transport": "sse",
      "url": "https://whatsapp-mcp-xxxxx-uc.a.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_GOOGLE_ID_TOKEN"
      }
    }
  }
}
```

#### Obtaining Google ID Tokens

To get a valid token for authentication:

```bash
# Generate a Google ID token with your OAuth Client ID as the audience
gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com
```

**Token Refresh**: Google ID tokens expire after 1 hour. You'll need to refresh the token periodically:
- Manually update the config file with a new token
- Or use a token refresh script/tool to automate token updates

#### Security Notes for Remote Access

- **Never commit tokens** to version control
- **Use environment variables** or secure credential storage for tokens
- **Rotate tokens** regularly and monitor access logs
- **Enable audit logging** in Secret Manager and Cloud Run
- **Consider VPC-SC** for additional network isolation

For detailed guides, see:
- [gcp/OAUTH_SETUP.md](gcp/OAUTH_SETUP.md) for OAuth troubleshooting
- [gcp/README.md](gcp/README.md) for Cloud Run deployment details
