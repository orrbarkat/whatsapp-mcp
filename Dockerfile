# Combined WhatsApp MCP Server Dockerfile
# Includes both Go (for bridge) and Python (for MCP server) runtimes
FROM golang:1.24-bookworm AS go-builder

# Install necessary packages for CGO
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy go mod files first for better caching
COPY whatsapp-bridge/go.mod whatsapp-bridge/go.sum ./
RUN go mod download

# Copy only Go source files for better cache invalidation
COPY whatsapp-bridge/*.go ./

# Enable CGO for sqlite3 and build the application
ENV CGO_ENABLED=1
RUN go build -o whatsapp-bridge main.go

# Final stage - Python with Go runtime
FROM python:3.11.9-slim-bookworm

# Set environment variables for non-interactive apt and home directory
ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/home/mcpuser

# Install system dependencies including ffmpeg, wget, and sqlite runtime library
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsqlite3-0 \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the compiled bridge binary and required static assets from builder stage
COPY --from=go-builder /build/whatsapp-bridge ./whatsapp-bridge/whatsapp-bridge
COPY whatsapp-bridge/status.html ./whatsapp-bridge/

# Install uv with pinned version for reproducibility
RUN pip install uv==0.4.22

# Copy Python requirements and install dependencies
COPY whatsapp-mcp-server/pyproject.toml whatsapp-mcp-server/uv.lock ./whatsapp-mcp-server/
WORKDIR /app/whatsapp-mcp-server
RUN uv sync --frozen

# Copy the MCP server source code
COPY whatsapp-mcp-server/ ./

# Create directories for data storage, create non-root user, and set permissions
RUN mkdir -p ../whatsapp-bridge/store ../qr-codes && \
    useradd -m -u 1000 mcpuser
RUN chown -R mcpuser:mcpuser /app/whatsapp-mcp-server && \
    chown -R mcpuser:mcpuser /app/whatsapp-bridge

RUN mkdir -p /home/mcpuser/.cache && \
    chown -R mcpuser:mcpuser /home/mcpuser/.cache

RUN chown -R mcpuser:mcpuser /app/whatsapp-mcp-server

USER mcpuser

# Expose both MCP server port and bridge API port
EXPOSE 3000 8080

# OCI metadata labels for traceability and Cloud Run compatibility
LABEL org.opencontainers.image.description="WhatsApp MCP Server with integrated Go bridge for Claude Desktop integration"
LABEL org.opencontainers.image.source="https://github.com/orrbarkat/whatsapp-mcp"
LABEL cloud.run.compatible="true"

# Healthcheck for local Docker and testing (Cloud Run ignores Docker HEALTHCHECK)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

# Run the MCP server - it will automatically manage the bridge process
# FastMCP automatically binds to 0.0.0.0 when running in SSE mode
# Use exec form to ensure proper signal handling (SIGTERM from Cloud Run)
CMD ["uv", "run", "main.py"]