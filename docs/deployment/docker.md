# Docker Deployment

This guide covers deploying the WhatsApp MCP server using Docker and Docker Compose.

## Overview

The WhatsApp MCP server supports containerized deployment using Docker and Docker Compose. The container includes both the Go bridge and Python MCP server in a single, optimized image that preserves all automatic bridge management features.

## Quick Start

1. **Build and start the container:**
   ```bash
   docker-compose up -d
   ```

2. **Access the QR code for authentication:**
   - Web interface: `http://localhost:8080/qr`
   - Status dashboard: `http://localhost:8080/status`

3. **Configure Claude Desktop** to use the containerized MCP server (see configuration below)

## Architecture

The Docker deployment uses a **combined container approach** that includes:

- **Go Bridge**: Compiled binary handling WhatsApp API communication
- **Go Runtime**: Available for automatic bridge process management
- **Python MCP Server**: Full MCP functionality with automatic bridge management
- **Shared Storage**: SQLite databases persisted via Docker volumes

This architecture ensures that all automatic bridge management features (startup, monitoring, QR code capture) work exactly as in local installations.

## Container Components

### Base Image

Uses a multi-stage build:
1. **Build stage**: Compiles Go bridge binary
2. **Runtime stage**: Combines Go runtime, Python, and dependencies

### Included Software

- Go 1.21+ (runtime and compiler)
- Python 3.11+
- UV package manager
- FFmpeg (for audio message conversion)
- SQLite3

### Exposed Ports

- **8080**: Bridge API endpoints (status, QR code, API)
- **3000**: MCP Server (SSE transport)

## MCP Transport Modes

The MCP server supports two transport modes, configurable via the `MCP_TRANSPORT` environment variable.

### STDIO Transport

**Use case:** Local development, direct MCP client connections

**Characteristics:**
- Communication via standard input/output streams
- Lower latency for local connections
- Requires direct process management

**Configuration:**
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

### SSE Transport (Default for Docker)

**Use case:** Containerized deployments, web-based integrations

**Characteristics:**
- Communication via HTTP Server-Sent Events
- Better suited for container environments
- Enables web-based MCP client connections
- Listens on port 3000 by default

**Configuration:**
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

## Environment Variables

Configure the Docker deployment using these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `sse` (Docker), `stdio` (local) | MCP transport protocol |
| `WHATSAPP_BRIDGE_URL` | `http://localhost:8080` | Bridge API endpoint (localhost in combined container) |
| `DATABASE_PATH` | `/app/whatsapp-bridge/store/messages.db` | SQLite database path |
| `WHATSAPP_DB_PATH` | `/app/whatsapp-bridge/store` | Bridge database directory |
| `DATABASE_URL` | (optional) | PostgreSQL connection string |
| `WHATSAPP_SESSION_DATABASE_URL` | (optional) | Session database connection string |
| `MCP_PORT` | `3000` | MCP server port (SSE mode) |

## Docker Compose Configuration

### Basic Configuration (SQLite)

The default `docker-compose.yml` uses SQLite for both messages and sessions:

```yaml
version: '3.8'

services:
  whatsapp-mcp:
    build: .
    container_name: whatsapp-mcp-server
    ports:
      - "8080:8080"  # Bridge API
      - "3000:3000"  # MCP Server
    environment:
      - MCP_TRANSPORT=sse
      - WHATSAPP_BRIDGE_URL=http://localhost:8080
    volumes:
      - whatsapp-data:/app/whatsapp-bridge/store
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  whatsapp-data:
```

### PostgreSQL Configuration

To use PostgreSQL for message storage, uncomment the PostgreSQL service and configure the environment:

```yaml
version: '3.8'

services:
  whatsapp-mcp:
    build: .
    container_name: whatsapp-mcp-server
    ports:
      - "8080:8080"
      - "3000:3000"
    environment:
      - MCP_TRANSPORT=sse
      - WHATSAPP_BRIDGE_URL=http://localhost:8080
      - DATABASE_URL=postgres://whatsapp:whatsapp_password@postgres:5432/whatsapp?sslmode=disable
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - whatsapp-data:/app/whatsapp-bridge/store
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: whatsapp-postgres
    environment:
      - POSTGRES_USER=whatsapp
      - POSTGRES_PASSWORD=whatsapp_password
      - POSTGRES_DB=whatsapp
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U whatsapp"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  whatsapp-data:
  postgres-data:
```

### Supabase Configuration

To use Supabase for database storage:

```yaml
services:
  whatsapp-mcp:
    environment:
      - MCP_TRANSPORT=sse
      - WHATSAPP_BRIDGE_URL=http://localhost:8080
      - DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?sslmode=require
      - WHATSAPP_SESSION_DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?sslmode=require
      - SUPABASE_URL=https://PROJECT.supabase.co
      - SUPABASE_KEY=YOUR_SERVICE_KEY
```

**Important**: Apply database migrations before starting:
```bash
# Run migrations
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql

# Start container
docker-compose up -d
```

## Database Configuration

### SQLite (Default)

SQLite databases are stored in a Docker volume for persistence:

```yaml
volumes:
  - whatsapp-data:/app/whatsapp-bridge/store
```

**Location**: `/app/whatsapp-bridge/store/` inside container
- `messages.db`: Message history
- `whatsapp.db`: WhatsApp session data

### PostgreSQL

Enable PostgreSQL by uncommenting the postgres service:

```yaml
# Uncomment the postgres service
postgres:
  image: postgres:15-alpine
  container_name: whatsapp-postgres
  # ... (see docker-compose.yml)
```

**Configure environment variables:**
```yaml
environment:
  # Uncomment and set DATABASE_URL
  - DATABASE_URL=postgres://whatsapp:whatsapp_password@postgres:5432/whatsapp?sslmode=disable
```

**Enable dependency:**
```yaml
# Uncomment depends_on
depends_on:
  postgres:
    condition: service_healthy
```

## Building the Container

### Build from Dockerfile

```bash
# Build the image
docker-compose build

# Or build with no cache
docker-compose build --no-cache
```

### Build with Custom Tag

```bash
# Build with specific tag
docker build -t whatsapp-mcp:v1.0.0 .

# Tag for registry
docker tag whatsapp-mcp:v1.0.0 your-registry/whatsapp-mcp:v1.0.0
```

## Running the Container

### Start Services

```bash
# Start in detached mode
docker-compose up -d

# Start with logs
docker-compose up

# Start specific service
docker-compose up -d whatsapp-mcp
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart whatsapp-mcp
```

## Claude Desktop Configuration

### With Docker Exec (Recommended)

Configure Claude Desktop to execute commands inside the running container:

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

Windows path: `%APPDATA%\Claude\claude_desktop_config.json`

### With SSE URL

Alternatively, connect to the running SSE server:

```json
{
  "mcpServers": {
    "whatsapp": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

## Monitoring and Logs

### View Container Logs

```bash
# Follow logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f whatsapp-mcp

# View last 100 lines
docker-compose logs --tail=100 whatsapp-mcp
```

### Check Container Status

```bash
# List running containers
docker-compose ps

# View container details
docker inspect whatsapp-mcp-server
```

### Health Checks

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' whatsapp-mcp-server

# View health check logs
docker inspect --format='{{json .State.Health}}' whatsapp-mcp-server | jq
```

## Accessing the Container

### Execute Commands

```bash
# Open bash shell
docker exec -it whatsapp-mcp-server bash

# Run specific command
docker exec whatsapp-mcp-server ps aux

# Check bridge status
docker exec whatsapp-mcp-server curl http://localhost:8080/api/status
```

### Copy Files

```bash
# Copy file from container
docker cp whatsapp-mcp-server:/app/whatsapp-bridge/store/messages.db ./messages.db

# Copy file to container
docker cp ./config.json whatsapp-mcp-server:/app/config.json
```

## Data Persistence

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect whatsapp-mcp_whatsapp-data

# Backup volume
docker run --rm -v whatsapp-mcp_whatsapp-data:/data -v $(pwd):/backup ubuntu tar czf /backup/whatsapp-backup.tar.gz /data

# Restore volume
docker run --rm -v whatsapp-mcp_whatsapp-data:/data -v $(pwd):/backup ubuntu tar xzf /backup/whatsapp-backup.tar.gz -C /
```

### Database Backups

```bash
# SQLite backup
docker exec whatsapp-mcp-server sqlite3 /app/whatsapp-bridge/store/messages.db ".backup '/app/whatsapp-bridge/store/messages_backup.db'"

# PostgreSQL backup
docker exec whatsapp-postgres pg_dump -U whatsapp whatsapp > backup.sql

# Restore PostgreSQL
docker exec -i whatsapp-postgres psql -U whatsapp whatsapp < backup.sql
```

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
docker-compose logs whatsapp-mcp
```

**Common issues**:
- Port already in use (8080 or 3000)
- Volume permission issues
- Missing environment variables

### Port Conflicts

**Find processes using ports**:
```bash
# Linux/macOS
lsof -i :8080
lsof -i :3000

# Or use netstat
netstat -tuln | grep 8080
```

**Change ports in docker-compose.yml**:
```yaml
ports:
  - "8081:8080"  # Use different host port
  - "3001:3000"
```

### Bridge Not Starting

**Check if bridge is running**:
```bash
docker exec whatsapp-mcp-server ps aux | grep main
```

**Manual bridge start**:
```bash
docker exec -d whatsapp-mcp-server /app/whatsapp-bridge/whatsapp-bridge
```

### Database Issues

**Check database files**:
```bash
docker exec whatsapp-mcp-server ls -lh /app/whatsapp-bridge/store/
```

**Run migrations**:
```bash
# For SQLite
docker exec whatsapp-mcp-server sqlite3 /app/whatsapp-bridge/store/messages.db < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For PostgreSQL
docker exec -i whatsapp-postgres psql -U whatsapp whatsapp < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

### Permission Issues

**Fix volume permissions**:
```bash
# Set correct ownership
docker exec whatsapp-mcp-server chown -R app:app /app/whatsapp-bridge/store
```

## Performance Optimization

### Resource Limits

Add resource limits to docker-compose.yml:

```yaml
services:
  whatsapp-mcp:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Build Optimization

Use build cache:
```bash
# Build with BuildKit
DOCKER_BUILDKIT=1 docker-compose build
```

## Security Considerations

### Network Isolation

Use Docker networks for isolation:
```yaml
services:
  whatsapp-mcp:
    networks:
      - whatsapp-network

networks:
  whatsapp-network:
    driver: bridge
```

### Read-Only Filesystem

Make most of the filesystem read-only:
```yaml
services:
  whatsapp-mcp:
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - whatsapp-data:/app/whatsapp-bridge/store:rw
```

### Run as Non-Root

The Dockerfile already creates a non-root user:
```dockerfile
RUN addgroup -g 1001 app && \
    adduser -D -u 1001 -G app app
USER app
```

## Additional Resources

- **Main Documentation**: [../../README.md](../../README.md)
- **Database Setup**: [../database.md](../database.md)
- **Migrations**: [../migrations.md](../migrations.md)
- **Networking**: [../networking.md](../networking.md)
- **Troubleshooting**: [../troubleshooting.md](../troubleshooting.md)
- **Docker Compose**: [../../docker-compose.yml](../../docker-compose.yml)
