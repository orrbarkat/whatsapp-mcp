-- Create chats table
CREATE TABLE chats (
    jid TEXT PRIMARY KEY,
    name TEXT,
    last_message_time TIMESTAMP
);

-- Create messages table
CREATE TABLE messages (
    id TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    sender TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    is_from_me BOOLEAN,
    media_type TEXT,
    filename TEXT,
    url TEXT,
    media_key BYTEA,
    file_sha256 BYTEA,
    file_enc_sha256 BYTEA,
    file_length BIGINT,
    PRIMARY KEY (id, chat_jid)
);
