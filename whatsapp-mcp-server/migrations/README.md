# Database Migrations

This directory contains SQL migration scripts for the Supabase database schema.

## Migration Files

### 001_create_chat_list_view.sql
Creates the `chat_list` view that aggregates chat information with the most recent message details. This view is used by the `SupabaseChatRepository.list_chats()` method to efficiently retrieve chat listings without relying on unsupported RPC chaining.

**Purpose:** Resolves the issue where supabase-py does not support chaining `.select()`, `.or_()`, `.order()`, and `.range()` on RPC function results.

**Implementation:** Uses a PostgreSQL view that LEFT JOINs `whatsmeow_chats` with `whatsmeow_history_messages` to provide all required fields in a single query.

## How to Apply Migrations

### Option 1: Supabase Dashboard (Recommended)
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of the migration file
4. Paste and execute the SQL

### Option 2: Supabase CLI
```bash
# If you have the Supabase CLI installed
supabase db push
```

### Option 3: Direct PostgreSQL Connection
```bash
# Connect to your Supabase database
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run the migration
\i migrations/001_create_chat_list_view.sql
```

## Verification

After applying the migration, verify the view is accessible:

```sql
-- Check the view exists
SELECT * FROM chat_list LIMIT 1;

-- Verify PostgREST access
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

The migration creates two indexes to optimize query performance:
- `idx_chats_last_message_time` on `whatsmeow_chats(last_message_time DESC)`
- `idx_messages_chat_timestamp` on `whatsmeow_history_messages(chat, timestamp DESC)`

These indexes improve sorting and joining operations when listing chats.

## Rollback

To rollback this migration:

```sql
DROP VIEW IF EXISTS chat_list;
DROP INDEX IF EXISTS idx_chats_last_message_time;
DROP INDEX IF EXISTS idx_messages_chat_timestamp;
```

Note: Dropping indexes may impact performance of other queries using these tables.
