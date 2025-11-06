-- Migration: Create base bridge tables for chats and messages
-- This migration creates the core schema required by the WhatsApp bridge
-- to store chat metadata and message history.
--
-- IMPORTANT: This migration must be run BEFORE starting the bridge.
-- The bridge will validate that these tables exist on startup.
--
-- Compatible with: SQLite and PostgreSQL

-- Create chats table
-- Stores metadata about individual chats and groups
CREATE TABLE IF NOT EXISTS chats (
    jid TEXT PRIMARY KEY,
    name TEXT,
    last_message_time TIMESTAMP
);

-- Create messages table
-- Stores message history including media metadata
-- Note: BLOB vs BYTEA and INTEGER vs BIGINT differ between SQLite and PostgreSQL
-- For SQLite: use BLOB and INTEGER
-- For PostgreSQL: use BYTEA and BIGINT (will be auto-converted by PostgreSQL)
CREATE TABLE IF NOT EXISTS messages (
    id TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    sender TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    is_from_me BOOLEAN,
    media_type TEXT,
    filename TEXT,
    url TEXT,
    -- Media encryption fields (binary data)
    media_key BLOB,        -- PostgreSQL: Will accept as BYTEA
    file_sha256 BLOB,      -- PostgreSQL: Will accept as BYTEA
    file_enc_sha256 BLOB,  -- PostgreSQL: Will accept as BYTEA
    file_length INTEGER,   -- PostgreSQL: Will accept as BIGINT
    PRIMARY KEY (id, chat_jid),
    FOREIGN KEY (chat_jid) REFERENCES chats(jid) ON DELETE CASCADE
);

-- Create indexes for performance optimization
-- Index on chats for sorting by last message time
CREATE INDEX IF NOT EXISTS idx_chats_last_message_time
    ON chats(last_message_time DESC);

-- Index on messages for chat-based queries and sorting
CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp
    ON messages(chat_jid, timestamp DESC);

-- Index on messages for sender-based queries
CREATE INDEX IF NOT EXISTS idx_messages_sender
    ON messages(sender);

-- PostgreSQL-specific adjustments
-- If running on PostgreSQL, these ALTER statements will fix the types
-- SQLite will ignore these as they don't support ALTER COLUMN TYPE

-- Note: Uncomment these lines if you need explicit type conversion for PostgreSQL
-- and are importing from SQLite. Otherwise, creating tables fresh in PostgreSQL
-- should use the correct types from the start.

-- For PostgreSQL fresh installation, you may want to create with explicit types:
-- CREATE TABLE messages (
--     ...
--     media_key BYTEA,
--     file_sha256 BYTEA,
--     file_enc_sha256 BYTEA,
--     file_length BIGINT,
--     ...
-- );
