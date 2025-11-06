# Quick Start Guide

This guide will help you get the WhatsApp MCP server running quickly.

## Prerequisites

- Go 1.20+
- Python 3.6+
- UV package manager
- FFmpeg (optional, for audio messages)

## Quick Start with SQLite (Default)

```bash
# 1. Start both bridge and MCP server
./start-mcp.sh start

# 2. Scan QR code
# Open http://localhost:8080/qr in your browser and scan with WhatsApp

# 3. The MCP server is now running on http://localhost:3000
```

## Quick Start with Supabase

```bash
# 1. Copy the example env file
cp .env.example .env

# 2. Edit .env and add your Supabase connection string
nano .env
# Uncomment and set:
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# 3. Start both services
./start-mcp.sh start

# 4. Scan QR code
# Open http://localhost:8080/qr in your browser and scan with WhatsApp

# 5. Connect your MCP client to http://localhost:3000 (SSE transport)
```

## Script Commands

```bash
# Start both bridge and MCP server
./start-mcp.sh start

# Check status of all services
./start-mcp.sh status

# View bridge logs
./start-mcp.sh logs bridge

# View MCP server logs
./start-mcp.sh logs mcp

# Stop all services
./start-mcp.sh stop

# Restart all services
./start-mcp.sh restart

# Show help
./start-mcp.sh help
```

## Using with Supabase

### Method 1: Using .env file (Recommended)

```bash
# 1. Create .env from template
cp .env.example .env

# 2. Edit .env
nano .env

# 3. Set your Supabase connection string
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

# 4. Start services
./start-mcp.sh start
```

### Method 2: One-time environment variable

```bash
DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres" ./start-mcp.sh start
```

### Method 3: Export environment variable

```bash
export DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"
./start-mcp.sh start
```

## Service Ports

- **Bridge API**: http://localhost:8080
- **QR Code**: http://localhost:8080/qr
- **Status Dashboard**: http://localhost:8080/status
- **MCP Server**: http://localhost:3000 (SSE transport)

## Connecting to Claude Desktop

The script starts the MCP server with SSE transport on port 3000. You have two options:

### Option A: Use the running SSE server

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "whatsapp": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

### Option B: Let Claude Desktop manage the process (Recommended)

Stop the script-managed services and let Claude Desktop start them:

```bash
./start-mcp.sh stop
```

Then configure Claude Desktop to start the MCP server in STDIO mode:

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
      ],
      "env": {
        "DATABASE_URL": "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"
      }
    }
  }
}
```

## Troubleshooting

**Port already in use:**
```bash
# Stop all services
./start-mcp.sh stop

# Check specific port
lsof -i :8080  # Bridge
lsof -i :3000  # MCP Server
```

**Check service status:**
```bash
./start-mcp.sh status
```

**View detailed logs:**
```bash
# Bridge logs
./start-mcp.sh logs bridge

# MCP server logs
./start-mcp.sh logs mcp

# Or view log files directly
tail -f bridge.log
tail -f mcp_server.log
```

**Services not starting:**
```bash
# Check prerequisites
which go
which uv
which python3

# Check log files for errors
cat bridge.log
cat mcp_server.log
```

**QR code not showing:**
- Wait 5-10 seconds after starting
- Check bridge status: `./start-mcp.sh status`
- Refresh the QR page: http://localhost:8080/qr
- Check bridge logs: `./start-mcp.sh logs bridge`

**Database connection issues:**
```bash
# Test PostgreSQL connection
psql "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres" -c "SELECT 1;"

# Check if DATABASE_URL is set
echo $DATABASE_URL

# Verify .env file is loaded
./start-mcp.sh start  # Should show "Loading environment variables from .env file"
```

## Files Created

- `bridge.log` - Bridge application logs
- `mcp_server.log` - MCP server logs
- `bridge.pid` - Bridge process ID
- `mcp_server.pid` - MCP server process ID
- `.env` - Your local configuration (gitignored)
- `whatsapp-bridge/store/` - Database files (SQLite) or session data

## Clean Restart

```bash
# Stop everything
./start-mcp.sh stop

# Remove old logs
rm -f bridge.log mcp_server.log

# Remove PIDs
rm -f bridge.pid mcp_server.pid

# Start fresh
./start-mcp.sh start
```

## Production Deployment

For production, consider using:

1. **Google Cloud Platform** - Fully managed deployment with Cloud Run, Cloud SQL, and Cloud Storage
   ```bash
   export GCP_PROJECT_ID=your-project-id
   ./gcp/setup.sh  # Automated provisioning
   ```
   See [README.md - GCP Deployment](README.md#deploying-to-google-cloud-platform-gcp) for details.

2. **Docker Compose** - Containerized deployment (see docker-compose.yml)
   ```bash
   docker-compose up -d
   ```

3. **Systemd service** (Linux) - Example service files available in the repository

4. **Process manager** - PM2 or supervisord for process management

For more detailed information, see [README.md](README.md).
