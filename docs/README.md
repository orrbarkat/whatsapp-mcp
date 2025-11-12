# WhatsApp MCP Server Documentation

Welcome to the WhatsApp MCP Server documentation! This index helps you quickly find the information you need.

## Glossary

To ensure consistency throughout the documentation, we use these terms:

- **Bridge** or **Go Bridge**: The Go application (`whatsapp-bridge/`) that connects to WhatsApp's web API and stores message history
- **MCP Server** or **Python Server**: The Python server (`whatsapp-mcp-server/`) implementing the Model Context Protocol
- **Messages Database**: PostgreSQL/SQLite database storing chat history and message content (configured via `DATABASE_URL`)
- **Sessions Database**: PostgreSQL/SQLite database storing WhatsApp authentication data (configured via `WHATSAPP_SESSION_DATABASE_URL`)
- **SSE Transport**: Server-Sent Events transport mode for HTTP-based MCP connections
- **STDIO Transport**: Standard input/output transport mode for direct process connections

## Quick Navigation

### Getting Started
- **[Main README](../README.md)** - Introduction, installation, and 5-minute quickstart
- **[Environment Variables](../SECRETS_REFERENCE.md)** - Complete secrets and configuration reference

### Common Tasks

#### Setup and Configuration
- [Install Prerequisites](../README.md#prerequisites)
- [Connect to Claude Desktop or Cursor](../README.md#connect-to-the-mcp-server)
- [Configure Database Backend](database.md)
- [Run Database Migrations](migrations.md)
- [Configure Environment Variables](../SECRETS_REFERENCE.md)

#### Deployment
- [Run with Docker Compose](deployment/docker.md)
- [Deploy to Google Cloud Run](deployment/cloud-run.md)
- [Configure Networking and Ports](networking.md)

#### Platform-Specific
- [Windows Setup (CGO and MSYS2)](platforms/windows.md)

#### Monitoring and Maintenance
- [Check Bridge and Sync Status](status.md)
- [Troubleshoot Common Issues](troubleshooting.md)

### Documentation by Topic

#### Database
- **[Database Configuration](database.md)** - SQLite, PostgreSQL, and Supabase setup
- **[Database Migrations](migrations.md)** - Schema setup and migration instructions
- **[Environment Variables](../SECRETS_REFERENCE.md)** - `DATABASE_URL`, `WHATSAPP_SESSION_DATABASE_URL`, and related secrets

#### Deployment
- **[Docker Compose Deployment](deployment/docker.md)** - Containerized local deployment
- **[Cloud Run Deployment](deployment/cloud-run.md)** - GCP serverless deployment with OAuth

#### Monitoring
- **[Status Monitoring](status.md)** - Bridge health, sync status, and diagnostics

#### Networking
- **[Networking and Transport](networking.md)** - Ports, SSE vs STDIO, and client configuration

#### Troubleshooting
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

#### Platform-Specific
- **[Windows Setup](platforms/windows.md)** - CGO enablement and C compiler setup

## Reference Documentation

### Configuration
- **[SECRETS_REFERENCE.md](../SECRETS_REFERENCE.md)** - Authoritative environment variable reference
- **[.env.example](../.env.example)** - Template for local environment configuration
- **[gcp/env-template.yaml](../gcp/env-template.yaml)** - Cloud Run environment reference

### Migration Scripts
- **[whatsapp-mcp-server/migrations/](../whatsapp-mcp-server/migrations/)** - SQL migration files
- **[Migration Guide](migrations.md)** - How to apply migrations

### API and Tools
- [MCP Tools Reference](../README.md#mcp-tools)
- [MCP Resources Reference](../README.md#mcp-resources)
- [Status Endpoints](status.md)

## External Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [WhatsApp Web MultiDevice API (whatsmeow)](https://github.com/tulir/whatsmeow)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Supabase Documentation](https://supabase.com/docs)

## Contributing

When updating documentation, please:
1. Follow the established terminology in the Glossary above
2. Link to the canonical source for each topic (avoid duplication)
3. Update this index when adding new documentation files
4. Test all links and command examples before committing