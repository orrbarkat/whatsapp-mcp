# Database Configuration

This guide covers database configuration options for the WhatsApp MCP server.

## Database Types

The WhatsApp MCP server supports multiple database backends through the `DATABASE_URL` environment variable:

### SQLite (Default)

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

### PostgreSQL

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

### Supabase

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

## Configuration Matrix

The WhatsApp MCP server supports independent configuration of two database concerns:

| Database Type | Purpose | Environment Variable | Default |
|---------------|---------|---------------------|---------|
| **Messages** | Chat history, message content, media metadata | `DATABASE_URL` | SQLite: `file:store/messages.db` |
| **Sessions** | WhatsApp authentication, device keys, contacts | `WHATSAPP_SESSION_DATABASE_URL` | Falls back to `DATABASE_URL`, then SQLite: `file:store/whatsapp.db` |

### Supported Combinations

| Messages DB | Session DB | Use Case | Configuration |
|-------------|------------|----------|---------------|
| SQLite | SQLite | Default local development | No configuration needed |
| PostgreSQL/Supabase | PostgreSQL/Supabase (same) | Production with shared database | Set `DATABASE_URL` only |
| PostgreSQL/Supabase | PostgreSQL/Supabase (separate) | Production with isolated databases | Set both `DATABASE_URL` and `WHATSAPP_SESSION_DATABASE_URL` |
| SQLite | PostgreSQL/Supabase | Local messages, remote sessions | Set `WHATSAPP_SESSION_DATABASE_URL` only |
| PostgreSQL/Supabase | SQLite | Remote messages, local sessions | Set `DATABASE_URL` only |

### Environment Variable Precedence

```bash
# Messages database (used by Python MCP server and Go bridge)
DATABASE_URL → defaults to SQLite: file:store/messages.db

# Session database (used only by Go bridge for whatsmeow session storage)
WHATSAPP_SESSION_DATABASE_URL → falls back to DATABASE_URL → defaults to SQLite: file:store/whatsapp.db
```

## Example Configurations

### Local Development (Default)
```bash
# No configuration needed - uses SQLite for both
```

### Production: All Data in Supabase
```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
export SUPABASE_URL="https://[PROJECT].supabase.co"
export SUPABASE_KEY="[SERVICE-KEY]"
```

### Production: Separate Supabase Databases
```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
export WHATSAPP_SESSION_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
export SUPABASE_URL="https://[PROJECT].supabase.co"
export SUPABASE_KEY="[SERVICE-KEY]"
```

### Hybrid: Local Sessions, Remote Messages
```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres?sslmode=require"
# WHATSAPP_SESSION_DATABASE_URL not set, uses local SQLite
```

## Schema Management

### Database Schema Setup

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

### Type Mapping

| SQLite Type | PostgreSQL Type | Usage |
|-------------|-----------------|-------|
| `BLOB` | `BYTEA` | Media keys, file hashes |
| `INTEGER` | `BIGINT` | File sizes, IDs |
| `TEXT` | `TEXT` | Messages, names, JIDs |
| `TIMESTAMP` | `TIMESTAMP` | Message times |
| `BOOLEAN` | `BOOLEAN` | Flags (is_from_me) |

### Quick Migration Commands

```bash
# For SQLite (local development)
sqlite3 store/messages.db < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For PostgreSQL (production/cloud)
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For Cloud SQL (see deployment guide for details)
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

For detailed migration instructions, see [migrations.md](migrations.md).

### Migration from SQLite to PostgreSQL

1. Export your SQLite data (if needed)
2. Set `DATABASE_URL` to your PostgreSQL connection string
3. Restart the bridge - schema will be created automatically
4. Import data (if migrating existing messages)

Note: The bridge does not automatically migrate data between database types. If you have existing data in SQLite that you want to preserve, you'll need to export and import it manually.

## Storing WhatsApp Sessions in Supabase

### Overview

By default, WhatsApp session data (authentication, device keys, contacts) is stored in local SQLite files. For production deployments, you can store sessions in Supabase Postgres for better persistence, backup, and multi-instance support.

### Step 1: Run Session Tables Migration

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

### Step 2: Verify Tables

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

### Step 3: Configure Session DSN

Set the `WHATSAPP_SESSION_DATABASE_URL` environment variable with your Supabase Postgres connection string:

```bash
# Format (ensure sslmode=require for Supabase)
export WHATSAPP_SESSION_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require"
```

**Important:** Use your Supabase **service key** (not anon key) for the Python MCP server, as the session tables have RLS enabled with deny-all policies.

### Step 4: Deploy with Session DSN

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

### Step 5: Verify

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

### Security Notes

- Session tables have Row Level Security (RLS) enabled with deny-all policies by default
- Only `service_role` can access session tables (anon/authenticated roles cannot)
- The Go bridge connects directly and bypasses RLS
- Client-side Supabase SDKs must never access session tables
- Store the service key in Secret Manager, not in environment variables

### GCS Backup Behavior

GCS session backup (`GCS_SESSION_BUCKET`) only works with SQLite sessions. If using Postgres/Supabase for sessions:
- GCS upload/download is automatically skipped
- Use Supabase's built-in backups or `pg_dump` for session backup
- Bridge logs will indicate "GCS session backup is only for SQLite, skipping"

### Troubleshooting

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

For complete migration documentation, see [migrations.md](migrations.md).

## Docker Database Configuration

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

See the [Docker deployment guide](deployment/docker.md) for complete Docker configuration details.
