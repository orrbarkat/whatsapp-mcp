# Quick Start Guide

This guide has been consolidated into the [main README](README.md#5-minute-quickstart).

## Where to Find What

- **5-Minute Quickstart**: See [README.md - 5-Minute Quickstart](README.md#5-minute-quickstart)
- **Service Ports**: See [docs/networking.md](docs/networking.md)
- **Using the `start-mcp.sh` script**: See [README.md - 5-Minute Quickstart](README.md#5-minute-quickstart)
- **Connecting to Claude Desktop**: See [README.md - Connect to Claude Desktop or Cursor](README.md#connect-to-claude-desktop-or-cursor)
- **Database Configuration**: See [docs/database.md](docs/database.md)
- **Troubleshooting**: See [docs/troubleshooting.md](docs/troubleshooting.md)

## Quick Command Reference

```bash
# Start all services
./start-mcp.sh start

# Check status
./start-mcp.sh status

# View logs
./start-mcp.sh logs bridge  # Bridge logs
./start-mcp.sh logs mcp     # MCP server logs

# Stop all services
./start-mcp.sh stop

# Restart all services
./start-mcp.sh restart
```

## QR Code and Status

- **QR Code**: http://localhost:8080/qr
- **Status Dashboard**: http://localhost:8080/status
- **MCP Server**: http://localhost:3000 (SSE transport)

For complete documentation, see the [main README](README.md) or [documentation index](docs/README.md).
