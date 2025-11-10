# Database Migrations

This directory contains SQL migration scripts for the WhatsApp MCP database schema. These migrations are compatible with both PostgreSQL (including Supabase) and SQLite databases.

## Migration Order

**IMPORTANT**: Migrations must be applied in numerical order. The base schema migration `000_create_bridge_tables.sql` must be applied first before any other migrations.

## ⚠️ Critical: Migrations Are NOT Automatic

**Migrations must be run manually BEFORE starting the application.** The WhatsApp bridge does NOT automatically apply migrations. If you attempt to start the bridge without first applying the required migrations, it will fail with an error about missing tables.

**For Supabase users:**
1. Apply migrations to your Supabase database BEFORE starting the container
2. Use `psql $DATABASE_URL -f migrations/000_create_bridge_tables.sql`
3. Apply subsequent migration files in numerical order
4. Verify tables exist before starting the application

See the "How to Apply Migrations" section below for detailed instructions.

## Migration Files

### 000_create_bridge_tables.sql
Creates the core `chats` and `messages` tables required by the WhatsApp bridge. This migration is **mandatory** and must be run before starting the bridge.

**Purpose:** Establishes the base schema for storing chat metadata and message history.

**Tables Created:**
- `chats`: Stores chat/group metadata (jid, name, last_message_time)
- `messages`: Stores message history with media metadata support

**Database Support:** Compatible with both SQLite and PostgreSQL. The migration uses compatible types that work across both databases, with BLOB/BYTEA and INTEGER/BIGINT fields adapting to the target database.

**Requirement:** The WhatsApp bridge validates that these tables exist on startup and will fail if they are missing.

### 001_create_chat_list_view.sql
Creates the `chat_list` view that aggregates chat information with the most recent message details. This view is used by the `SupabaseChatRepository.list_chats()` method to efficiently retrieve chat listings without relying on unsupported RPC chaining.

**Purpose:** Resolves the issue where supabase-py does not support chaining `.select()`, `.or_()`, `.order()`, and `.range()` on RPC function results.

**Implementation:** Uses a PostgreSQL view that LEFT JOINs `chats` with `messages` (the bridge-managed tables) to provide all required fields in a single query.

**Dependencies:** Requires `000_create_bridge_tables.sql` to be applied first.

### 010_create_whatsmeow_session_tables.sql
Creates all tables required by `go.mau.fi/whatsmeow/store/sqlstore` for storing WhatsApp session data in Postgres. This migration is **required** when using Postgres (including Supabase) as the session store backend.

**Purpose:** Establishes the schema for whatsmeow's SQLite-compatible tables adapted for Postgres. Enables storing WhatsApp device sessions, encryption keys, contacts, and sync state in a centralized database instead of local SQLite files.

**Tables Created:**
- `devices`: WhatsApp device registration and keys
- `identities`: Identity keys for other users
- `prekeys`, `signed_prekeys`: Signal protocol pre-keys
- `sessions`: Signal protocol sessions
- `sender_keys`: Group message encryption keys
- `app_state_sync_keys`, `app_state_version`, `app_state_mutation_macs`: Multi-device sync state
- `contacts`: Contact information
- `chat_settings`: Per-chat preferences (muted, pinned, archived)
- `message_secrets`: Message encryption keys
- `privacy_tokens`: Privacy feature tokens

**Database Support:** PostgreSQL only (including Supabase). Uses `bytea` for binary data and `timestamptz` for timestamps.

**Security:** Implements Row Level Security (RLS) with deny-all policies by default. Access is granted only to `service_role`, ensuring client-side SDKs cannot access sensitive session data. **The backend must use the Supabase service key** (not anon key) to access these tables.

**Dependencies:** None. Can be applied independently of message tables. Run order: apply after `000_` and `001_` if using Supabase for both messages and sessions.

## How to Apply Migrations

### For SQLite (Local Development)

```bash
# Navigate to the project root directory
cd whatsapp-mcp

# Run the base schema migration (required)
sqlite3 whatsapp-bridge/store/messages.db < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# Run additional migrations in order
sqlite3 whatsapp-bridge/store/messages.db < whatsapp-mcp-server/migrations/001_create_chat_list_view.sql
```

### For PostgreSQL (Production/Cloud)

```bash
# Set your DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:5432/dbname"

# Run the base schema migration (required)
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# Run additional migrations in order
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/001_create_chat_list_view.sql
```

### For Supabase

**CRITICAL**: Run these migrations BEFORE starting your Docker container or application. The application will fail to start if tables are missing.

#### Option 1: Using psql (Recommended for automation)
```bash
# Set your DATABASE_URL (include ?sslmode=require for Supabase)
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres?sslmode=require"

# Run migrations in order
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/001_create_chat_list_view.sql

# If using Supabase for session storage (requires migration 010):
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
```

#### Option 2: Supabase Dashboard (Recommended for manual setup)
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `000_create_bridge_tables.sql`
4. Paste and execute the SQL
5. Repeat for `001_create_chat_list_view.sql` and other migrations in order

#### Option 3: Direct PostgreSQL Connection
```bash
# Connect to your Supabase database
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres?sslmode=require"

# Run migrations in order
\i whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
\i whatsapp-mcp-server/migrations/001_create_chat_list_view.sql

# If using Supabase for session storage (recommended):
\i whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
```

**Note**: Always include `?sslmode=require` in your Supabase connection string for security.

## Verification

### Verify Base Tables (000_create_bridge_tables.sql)

```sql
-- Check that chats table exists and has correct structure
\d chats

-- Check that messages table exists and has correct structure
\d messages

-- Verify indexes were created
\di

-- Test inserting and querying (optional)
INSERT INTO chats (jid, name, last_message_time) VALUES ('test@s.whatsapp.net', 'Test Chat', NOW());
SELECT * FROM chats WHERE jid = 'test@s.whatsapp.net';
DELETE FROM chats WHERE jid = 'test@s.whatsapp.net';
```

### Verify Chat List View (001_create_chat_list_view.sql)

```sql
-- Check the view exists
SELECT * FROM chat_list LIMIT 1;

-- Verify PostgREST access (Supabase only)
-- In your browser or API client:
-- GET https://[YOUR-PROJECT-REF].supabase.co/rest/v1/chat_list
```

### Verify WhatsApp Session Tables (010_create_whatsmeow_session_tables.sql)

```sql
-- Check that the devices table exists (primary whatsmeow table)
SELECT to_regclass('public.devices');
-- Should return: "devices"

-- Verify all session tables exist
SELECT tablename FROM pg_tables WHERE schemaname = 'public'
AND tablename IN ('devices', 'identities', 'prekeys', 'sessions', 'sender_keys',
                  'signed_prekeys', 'app_state_sync_keys', 'app_state_version',
                  'app_state_mutation_macs', 'contacts', 'chat_settings',
                  'message_secrets', 'privacy_tokens');
-- Should return 13 rows

-- Verify RLS is enabled (should show all tables with RLS on)
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE '%'
AND tablename IN ('devices', 'identities', 'prekeys', 'sessions');
-- All should show rowsecurity = true

-- Verify service_role has access (must be connected as service_role)
SELECT grantee, privilege_type FROM information_schema.table_privileges
WHERE table_name = 'devices' AND grantee = 'service_role';
-- Should show SELECT, INSERT, UPDATE, DELETE

-- Verify anon/authenticated do NOT have direct access (security check)
SELECT grantee, privilege_type FROM information_schema.table_privileges
WHERE table_name = 'devices' AND grantee IN ('anon', 'authenticated');
-- Should return no rows (empty)
```

## View Schema

The `chat_list` view provides the following columns:

| Column | Type | Description |
|--------|------|-------------|
| jid | text | Chat JID (unique identifier) |
| name | text | Chat display name |
| last_message_time | timestamp | Timestamp of the most recent message |
| last_message | text | Content of the most recent message |
| last_sender | text | JID of the sender of the last message |
| last_is_from_me | boolean | Whether the last message was sent by the authenticated user |

## Permissions

The migration script grants SELECT permissions to the following roles:
- `anon` - For unauthenticated API access
- `authenticated` - For authenticated API access

Adjust these permissions based on your security requirements.

## Performance Considerations

The base migration (000_create_bridge_tables.sql) creates indexes that optimize the chat_list view:
- `idx_chats_last_message_time` on `chats(last_message_time DESC)`
- `idx_messages_chat_timestamp` on `messages(chat_jid, timestamp DESC)`

These indexes improve sorting and joining operations when listing chats.

## Rollback

### Rollback Base Tables (000_create_bridge_tables.sql)

**WARNING**: This will delete all chat and message data!

```sql
-- Drop tables (will also drop dependent objects like the chat_list view)
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS chats CASCADE;

-- Drop indexes (if tables weren't dropped)
DROP INDEX IF EXISTS idx_chats_last_message_time;
DROP INDEX IF EXISTS idx_messages_chat_timestamp;
DROP INDEX IF EXISTS idx_messages_sender;
```

### Rollback Chat List View (001_create_chat_list_view.sql)

```sql
DROP VIEW IF EXISTS chat_list;
```

Note: The indexes created in the base migration (idx_chats_last_message_time, idx_messages_chat_timestamp) should not be dropped unless you're also rolling back the base migration, as they improve performance for other queries.
