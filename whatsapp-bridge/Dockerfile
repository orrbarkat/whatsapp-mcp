# syntax=docker/dockerfile:1

# --- Builder stage ---
FROM golang:1.24-bookworm AS builder
WORKDIR /src

# Enable CGO for go-sqlite3
ENV CGO_ENABLED=1

# Copy all sources
COPY . .

# Build the whatsapp-bridge binary
WORKDIR /src/whatsapp-bridge
RUN go build -o /out/whatsapp-bridge .

# --- Runtime stage ---
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary
COPY --from=builder /out/whatsapp-bridge /app/whatsapp-bridge

# Create store directory for volumes
RUN mkdir -p /app/store

ENV PORT=8080
EXPOSE 8080

# Health check (Cloud Run also supports platform checks)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD ["/bin/sh", "-c", "wget -qO- http://127.0.0.1:${PORT}/healthz || exit 1"]

ENTRYPOINT ["/app/whatsapp-bridge"]
