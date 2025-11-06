# Database Migrations

This directory contains SQL migration scripts for the WhatsApp MCP database schema. These migrations are compatible with both PostgreSQL (including Supabase) and SQLite databases.

## Migration Order

**IMPORTANT**: Migrations must be applied in numerical order. The base schema migration `000_create_bridge_tables.sql` must be applied first before any other migrations.

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

#### Option 1: Supabase Dashboard (Recommended)
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `000_create_bridge_tables.sql`
4. Paste and execute the SQL
5. Repeat for `001_create_chat_list_view.sql` and other migrations in order

#### Option 2: Supabase CLI
```bash
# If you have the Supabase CLI installed
supabase db push
```

#### Option 3: Direct PostgreSQL Connection
```bash
# Connect to your Supabase database
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run migrations in order
\i whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
\i whatsapp-mcp-server/migrations/001_create_chat_list_view.sql
```

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
