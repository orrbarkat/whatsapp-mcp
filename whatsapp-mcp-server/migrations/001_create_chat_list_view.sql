-- Migration: Create chat_list view for efficient chat listing with last message info
-- This view aggregates chat information with their most recent messages
-- to support the list_chats() API without requiring RPC chaining.
--
-- Usage: PostgREST will automatically expose this view as an API endpoint
-- at /chat_list once created. Ensure the appropriate permissions are set.

-- Drop view if it exists (for re-running the migration)
DROP VIEW IF EXISTS chat_list;

-- Create the chat_list view
-- This view joins chats with their most recent message to provide
-- all the fields needed by the ChatRepository.list_chats() method.
CREATE VIEW chat_list AS
SELECT
    c.jid,
    c.name,
    c.last_message_time,
    m.content AS last_message,
    m.sender AS last_sender,
    m.is_from_me AS last_is_from_me
FROM
    chats c
LEFT JOIN
    messages m
    ON c.jid = m.chat_jid
    AND c.last_message_time = m.timestamp;

-- Grant permissions for PostgREST access
-- Adjust the role name based on your Supabase configuration
-- Common roles: anon, authenticated, service_role
GRANT SELECT ON chat_list TO anon;
GRANT SELECT ON chat_list TO authenticated;

-- Note: Indexes are created by the base migration (000_create_bridge_tables.sql)
-- These indexes optimize the view queries:
-- - idx_chats_last_message_time on chats(last_message_time DESC)
-- - idx_messages_chat_timestamp on messages(chat_jid, timestamp DESC)
-- No need to recreate them here.

-- Notes for deployment:
-- 1. Run this SQL in your Supabase SQL Editor or via migration tool
-- 2. Verify the view is accessible via PostgREST: GET /rest/v1/chat_list
-- 3. Ensure the anon/authenticated roles have SELECT permissions on the view
-- 4. The view will be automatically available to the Supabase Python client
--    as a table: client.table("chat_list").select("*")
