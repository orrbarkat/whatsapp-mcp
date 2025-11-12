# Networking and Transport

This guide covers networking configuration, transport modes, and client connectivity for the WhatsApp MCP server.

## Overview

The WhatsApp MCP server uses two primary network components:

1. **WhatsApp Bridge** (Go): HTTP server on port 8080
2. **MCP Server** (Python): Supports STDIO and SSE transport modes

## Bridge Endpoints (Port 8080)

The WhatsApp Bridge provides HTTP endpoints for communication and monitoring:

### Primary Endpoints

- **`http://localhost:8080/api/status`**: JSON status data
  - Bridge health and authentication state
  - Database statistics
  - Last sync timestamp

- **`http://localhost:8080/qr`**: QR code page
  - Displays authentication QR code
  - Used for initial setup and re-authentication

- **`http://localhost:8080/status`**: Status dashboard
  - Visual HTML dashboard
  - Auto-refreshing status display
  - Color-coded status indicators

### Additional Endpoints

- **`http://localhost:8080/api/session-backend`**: Session storage info
  - Shows SQLite or Postgres backend
  - Connection validation status

## MCP Transport Modes

The MCP server supports two transport protocols, configurable via the `MCP_TRANSPORT` environment variable.

### STDIO Transport

**Default for**: Local installations, direct MCP client connections

**Characteristics**:
- Communication via standard input/output streams
- Lower latency for local connections
- Requires direct process management
- Best for Claude Desktop managing the process

**Configuration**:
```bash
# Set transport mode
export MCP_TRANSPORT=stdio

# Start server
uv run main.py
```

**Claude Desktop Config**:
```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "uv",
      "args": ["--directory", "/path/to/whatsapp-mcp-server", "run", "main.py"],
      "env": {
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

**Advantages**:
- Lower latency
- Direct process control
- Native MCP client integration
- No network ports required

**Limitations**:
- Single client only
- Requires local process access
- Not suitable for remote connections

### SSE Transport (Server-Sent Events)

**Default for**: Docker deployments, containerized environments, remote access

**Characteristics**:
- Communication via HTTP Server-Sent Events
- Better suited for container environments
- Enables web-based MCP client connections
- Listens on port 3000 by default

**Configuration**:
```bash
# Set transport mode
export MCP_TRANSPORT=sse
export MCP_PORT=3000

# Start server
uv run main.py
```

**Claude Desktop Config**:
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

**Advantages**:
- Container-friendly
- Supports remote connections
- Multiple clients possible
- Web-based integration
- Better for production deployments

**Limitations**:
- Slightly higher latency
- Requires open network port (3000)
- HTTP-based overhead

## Port Configuration

### Default Ports

| Component | Port | Purpose | Configurable |
|-----------|------|---------|--------------|
| Bridge API | 8080 | WhatsApp bridge HTTP endpoints | No |
| MCP Server | 3000 | SSE transport (when enabled) | Yes (MCP_PORT) |

### Customizing MCP Port

```bash
# Set custom port for SSE transport
export MCP_PORT=8000

# Cloud Run uses PORT environment variable
export PORT=8000
export MCP_PORT=8000
```

### Port Conflicts

If ports are already in use:

```bash
# Check what's using a port
lsof -i :8080
lsof -i :3000

# Kill process using port
kill $(lsof -t -i:8080)
kill $(lsof -t -i:3000)
```

## Client Configuration

### Local Development

**Option A: STDIO (Recommended)**

Let Claude Desktop manage the MCP server process:

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

**Option B: SSE (Alternative)**

Run MCP server separately and connect via HTTP:

```bash
# Start MCP server with SSE
export MCP_TRANSPORT=sse
./start-mcp.sh start
```

```json
{
  "mcpServers": {
    "whatsapp": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

### Docker Deployment

Use SSE transport for containerized deployment:

```yaml
# docker-compose.yml
environment:
  - MCP_TRANSPORT=sse
  - MCP_PORT=3000
  - WHATSAPP_BRIDGE_URL=http://localhost:8080
ports:
  - "3000:3000"  # MCP Server
  - "8080:8080"  # Bridge API
```

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "docker",
      "args": ["exec", "-i", "whatsapp-mcp-server", "uv", "run", "main.py"]
    }
  }
}
```

### Remote Access (Cloud Run)

Use SSE transport with authentication:

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

## Transport Mode Comparison

| Aspect | STDIO | SSE |
|--------|-------|-----|
| **Latency** | Lower | Slightly higher |
| **Docker Support** | Limited | Excellent |
| **Web Integration** | Not suitable | Native support |
| **Process Management** | Direct | Via HTTP |
| **Debugging** | Terminal logs | HTTP logs + browser tools |
| **Scalability** | Single instance | Multiple clients possible |
| **Remote Access** | No | Yes |
| **Port Requirements** | None | Port 3000 |

## Recommended Configurations

### Local Development
```bash
# Use STDIO transport with direct Python execution
MCP_TRANSPORT=stdio
# Let Claude Desktop manage the process
```

### Development with Docker
```bash
# Use SSE transport for consistency with production
MCP_TRANSPORT=sse
MCP_PORT=3000
```

### Production Docker
```bash
# Use SSE transport with Docker Compose
MCP_TRANSPORT=sse
MCP_PORT=3000
WHATSAPP_BRIDGE_URL=http://localhost:8080
```

### Production Cloud Run
```bash
# Use SSE transport with OAuth
MCP_TRANSPORT=sse
PORT=3000
MCP_PORT=3000
OAUTH_ENABLED=true
WHATSAPP_BRIDGE_URL=http://localhost:8080
```

## Firewall Configuration

### Local Development

No firewall configuration needed for STDIO transport.

For SSE transport, ensure ports are accessible:
```bash
# macOS - Allow incoming connections
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/python
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/go

# Linux - Using ufw
sudo ufw allow 8080/tcp
sudo ufw allow 3000/tcp
```

### Docker Deployment

Ports are mapped in docker-compose.yml:
```yaml
ports:
  - "8080:8080"  # Bridge API
  - "3000:3000"  # MCP Server (SSE)
```

### Cloud Run

Cloud Run handles ingress automatically. Configure ingress controls if needed:
```bash
gcloud run services update whatsapp-mcp \
  --ingress=internal-and-cloud-load-balancing
```

## Network Troubleshooting

### Connection Refused

**Issue**: Cannot connect to bridge or MCP server

**Solutions**:
1. Verify processes are running
2. Check port availability: `lsof -i :8080` and `lsof -i :3000`
3. Verify firewall settings
4. Check if using correct transport mode

### Bridge Not Reachable

**Issue**: MCP server cannot reach bridge

**Solutions**:
1. Verify `WHATSAPP_BRIDGE_URL` is set correctly
2. For Docker: use `http://localhost:8080` (same container)
3. For separate containers: use container name or host IP
4. Check bridge is running: `curl http://localhost:8080/api/status`

### SSE Connection Timeout

**Issue**: SSE transport times out

**Solutions**:
1. Verify MCP_PORT is correct
2. Check port is not blocked
3. Ensure MCP_TRANSPORT=sse is set
4. Review server logs for errors

### STDIO Not Working

**Issue**: STDIO transport fails

**Solutions**:
1. Verify MCP_TRANSPORT=stdio (or unset for default)
2. Check Claude Desktop has correct command path
3. Ensure Python and uv are in PATH
4. Review Claude Desktop logs

## Environment Variables Reference

### Transport Configuration

```bash
# MCP Transport mode
MCP_TRANSPORT=sse  # or 'stdio' (default for local)

# MCP Server port (SSE mode only)
MCP_PORT=3000

# Cloud Run port (set by Cloud Run, or override)
PORT=3000

# Bridge URL (for MCP server to communicate with bridge)
WHATSAPP_BRIDGE_URL=http://localhost:8080
```

### Docker Compose Example

```yaml
environment:
  - MCP_TRANSPORT=sse
  - MCP_PORT=3000
  - WHATSAPP_BRIDGE_URL=http://localhost:8080
  - DATABASE_URL=${DATABASE_URL}
```

### Cloud Run Example

```bash
gcloud run deploy whatsapp-mcp \
  --set-env-vars=MCP_TRANSPORT=sse,PORT=3000,MCP_PORT=3000,WHATSAPP_BRIDGE_URL=http://localhost:8080
```

## Additional Resources

- **Docker Deployment**: See [deployment/docker.md](deployment/docker.md)
- **Cloud Run Deployment**: See [deployment/cloud-run.md](deployment/cloud-run.md)
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)
- **MCP Specification**: [Model Context Protocol](https://modelcontextprotocol.io)
