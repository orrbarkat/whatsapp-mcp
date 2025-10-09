# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

# Install ffmpeg for audio conversion and minimal tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the MCP server directory
COPY . /app

# Install runtime dependencies directly (pyproject lists deps but has no build-system)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi uvicorn[standard] google-auth httpx requests "mcp[cli]>=1.6.0"

# Default to HTTP transport on Cloud Run; PORT is provided by platform
ENV TRANSPORT_MODE=http
ENV PORT=8080
EXPOSE 8080

# Health checks can use /healthz
CMD ["python", "server.py", "--transport=http"]
