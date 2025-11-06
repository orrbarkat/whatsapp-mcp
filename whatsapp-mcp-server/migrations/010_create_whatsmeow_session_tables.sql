-- Migration: Create whatsmeow session tables for Postgres
-- This schema matches the structure expected by go.mau.fi/whatsmeow/store/sqlstore
-- All tables use timestamptz for timestamps and bytea for binary data

-- Device table stores WhatsApp device information
CREATE TABLE IF NOT EXISTS devices (
    jid TEXT PRIMARY KEY,
    registration_id BIGINT NOT NULL,
    noise_key BYTEA NOT NULL,
    identity_key BYTEA NOT NULL,
    signed_pre_key BYTEA NOT NULL,
    signed_pre_key_id INTEGER NOT NULL,
    signed_pre_key_sig BYTEA NOT NULL,
    adv_key BYTEA NOT NULL,
    adv_details BYTEA NOT NULL,
    adv_account_sig BYTEA NOT NULL,
    adv_account_sig_key BYTEA NOT NULL,
    adv_device_sig BYTEA NOT NULL,
    platform TEXT NOT NULL DEFAULT '',
    business_name TEXT NOT NULL DEFAULT '',
    push_name TEXT NOT NULL DEFAULT ''
);

-- Identities table stores identity keys for other users
CREATE TABLE IF NOT EXISTS identities (
    our_jid TEXT NOT NULL,
    their_id TEXT NOT NULL,
    identity BYTEA NOT NULL,
    PRIMARY KEY (our_jid, their_id)
);

-- Pre-keys table stores pre-keys for the device
CREATE TABLE IF NOT EXISTS prekeys (
    jid TEXT NOT NULL,
    key_id INTEGER NOT NULL,
    key BYTEA NOT NULL,
    uploaded BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (jid, key_id)
);

-- Sessions table stores Signal protocol sessions
CREATE TABLE IF NOT EXISTS sessions (
    our_jid TEXT NOT NULL,
    their_id TEXT NOT NULL,
    session BYTEA NOT NULL,
    PRIMARY KEY (our_jid, their_id)
);

-- Sender keys table stores sender keys for group messages
CREATE TABLE IF NOT EXISTS sender_keys (
    our_jid TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    sender_key BYTEA NOT NULL,
    PRIMARY KEY (our_jid, chat_id, sender_id)
);

-- Signed pre-keys table stores signed pre-keys
CREATE TABLE IF NOT EXISTS signed_prekeys (
    jid TEXT NOT NULL,
    key_id INTEGER NOT NULL,
    key BYTEA NOT NULL,
    timestamp BIGINT NOT NULL,
    uploaded BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (jid, key_id)
);

-- App state sync keys table stores keys for WhatsApp multi-device sync
CREATE TABLE IF NOT EXISTS app_state_sync_keys (
    jid TEXT NOT NULL,
    key_id BYTEA NOT NULL,
    key_data BYTEA NOT NULL,
    timestamp BIGINT NOT NULL,
    fingerprint BYTEA NOT NULL,
    PRIMARY KEY (jid, key_id)
);

-- App state version table stores sync state versions
CREATE TABLE IF NOT EXISTS app_state_version (
    jid TEXT NOT NULL,
    name TEXT NOT NULL,
    version BIGINT NOT NULL,
    hash BYTEA NOT NULL,
    PRIMARY KEY (jid, name)
);

-- App state mutation MACs table stores mutation verification data
CREATE TABLE IF NOT EXISTS app_state_mutation_macs (
    jid TEXT NOT NULL,
    name TEXT NOT NULL,
    version BIGINT NOT NULL,
    index_mac BYTEA NOT NULL,
    value_mac BYTEA,
    PRIMARY KEY (jid, name, version, index_mac)
);

-- Contacts table stores contact information
CREATE TABLE IF NOT EXISTS contacts (
    our_jid TEXT NOT NULL,
    their_jid TEXT NOT NULL,
    first_name TEXT NOT NULL DEFAULT '',
    full_name TEXT NOT NULL DEFAULT '',
    push_name TEXT NOT NULL DEFAULT '',
    business_name TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (our_jid, their_jid)
);

-- Chat settings table stores per-chat settings
CREATE TABLE IF NOT EXISTS chat_settings (
    our_jid TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    muted_until BIGINT NOT NULL DEFAULT 0,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (our_jid, chat_jid)
);

-- Message secrets table stores message encryption keys
CREATE TABLE IF NOT EXISTS message_secrets (
    our_jid TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    sender_jid TEXT NOT NULL,
    message_id TEXT NOT NULL,
    key BYTEA NOT NULL,
    timestamp BIGINT NOT NULL,
    PRIMARY KEY (our_jid, chat_jid, sender_jid, message_id)
);

-- Privacy tokens table stores tokens for privacy features
CREATE TABLE IF NOT EXISTS privacy_tokens (
    our_jid TEXT NOT NULL,
    their_jid TEXT NOT NULL,
    token BYTEA NOT NULL,
    timestamp BIGINT NOT NULL,
    PRIMARY KEY (our_jid, their_jid)
);

-- Enable Row Level Security on all session tables
-- By default, no access is granted to anon or authenticated roles
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE prekeys ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sender_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE signed_prekeys ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_state_sync_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_state_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_state_mutation_macs ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE privacy_tokens ENABLE ROW LEVEL SECURITY;

-- Create default deny-all policies
CREATE POLICY "Deny all access to devices" ON devices FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to identities" ON identities FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to prekeys" ON prekeys FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to sessions" ON sessions FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to sender_keys" ON sender_keys FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to signed_prekeys" ON signed_prekeys FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to app_state_sync_keys" ON app_state_sync_keys FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to app_state_version" ON app_state_version FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to app_state_mutation_macs" ON app_state_mutation_macs FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to contacts" ON contacts FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to chat_settings" ON chat_settings FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to message_secrets" ON message_secrets FOR ALL USING (FALSE);
CREATE POLICY "Deny all access to privacy_tokens" ON privacy_tokens FOR ALL USING (FALSE);

-- Grant access to service_role only (used by backend with service key)
-- Note: In Supabase, service_role bypasses RLS by default
-- These grants ensure the backend can access the tables
GRANT SELECT, INSERT, UPDATE, DELETE ON devices TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON identities TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON prekeys TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON sessions TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON sender_keys TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON signed_prekeys TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON app_state_sync_keys TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON app_state_version TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON app_state_mutation_macs TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON contacts TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON chat_settings TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON message_secrets TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON privacy_tokens TO service_role;

-- Create indices for common queries
CREATE INDEX IF NOT EXISTS idx_identities_our_jid ON identities(our_jid);
CREATE INDEX IF NOT EXISTS idx_prekeys_jid ON prekeys(jid);
CREATE INDEX IF NOT EXISTS idx_sessions_our_jid ON sessions(our_jid);
CREATE INDEX IF NOT EXISTS idx_sender_keys_our_jid_chat ON sender_keys(our_jid, chat_id);
CREATE INDEX IF NOT EXISTS idx_app_state_sync_keys_jid ON app_state_sync_keys(jid);
CREATE INDEX IF NOT EXISTS idx_app_state_version_jid ON app_state_version(jid);
CREATE INDEX IF NOT EXISTS idx_contacts_our_jid ON contacts(our_jid);
CREATE INDEX IF NOT EXISTS idx_chat_settings_our_jid ON chat_settings(our_jid);
CREATE INDEX IF NOT EXISTS idx_message_secrets_our_jid ON message_secrets(our_jid);
