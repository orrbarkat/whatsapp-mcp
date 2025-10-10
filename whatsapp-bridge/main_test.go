package main

import (
	"database/sql"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestPostgresDB(t *testing.T) {
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		t.Skip("DATABASE_URL not set, skipping postgres tests")
	}

	db, err := NewTestDB("postgres", databaseURL)
	require.NoError(t, err)
	defer db.Close()
	testDB(t, db)
}

func TestSQLiteDB(t *testing.T) {
	db, err := NewTestDB("sqlite3", "file:test.db?_foreign_keys=on")
	require.NoError(t, err)
	defer os.Remove("test.db")
	defer db.Close()
	testDB(t, db)
}

func NewTestDB(driver, dataSourceName string) (Database, error) {
	config := &DBConfig{
		driver:         driver,
		dataSourceName: dataSourceName,
	}

	db, err := sql.Open(config.driver, config.dataSourceName)
	if err != nil {
		return nil, fmt.Errorf("failed to open message database: %v", err)
	}

	var database Database
	if config.driver == "postgres" {
		database = &PostgresDB{db: db}
	} else {
		database = &SQLiteDB{db: db}
	}

	if err := database.Init(); err != nil {
		database.Close()
		return nil, fmt.Errorf("failed to initialize database: %v", err)
	}

	return database, nil
}


func testDB(t *testing.T, db Database) {
	// Test StoreChat and GetChatName
	err := db.StoreChat("123@s.whatsapp.net", "test-chat", time.Now())
	assert.NoError(t, err)

	name, err := db.GetChatName("123@s.whatsapp.net")
	assert.NoError(t, err)
	assert.Equal(t, "test-chat", name)

	// Test StoreChat conflict
	err = db.StoreChat("123@s.whatsapp.net", "test-chat-updated", time.Now())
	assert.NoError(t, err)
	name, err = db.GetChatName("123@s.whatsapp.net")
	assert.NoError(t, err)
	assert.Equal(t, "test-chat-updated", name)

	// Test StoreMessage and GetMessages
	now := time.Now().UTC().Truncate(time.Second)
	err = db.StoreMessage("msg1", "123@s.whatsapp.net", "sender1", "hello", now, false, "text", "", "", nil, nil, nil, 0)
	assert.NoError(t, err)

	messages, err := db.GetMessages("123@s.whatsapp.net", 1)
	assert.NoError(t, err)
	require.Len(t, messages, 1)
	assert.Equal(t, "sender1", messages[0].Sender)
	assert.Equal(t, "hello", messages[0].Content)
	assert.WithinDuration(t, now, messages[0].Time, time.Second)

	// Test StoreMessage conflict
	err = db.StoreMessage("msg1", "123@s.whatsapp.net", "sender1", "hello updated", now, false, "text", "", "", nil, nil, nil, 0)
	assert.NoError(t, err)
	messages, err = db.GetMessages("123@s.whatsapp.net", 1)
	assert.NoError(t, err)
	require.Len(t, messages, 1)
	assert.Equal(t, "hello updated", messages[0].Content)

	// Test GetChats
	chats, err := db.GetChats()
	assert.NoError(t, err)
	assert.Contains(t, chats, "123@s.whatsapp.net")

	// Test StoreMediaInfo and GetMediaInfo
	err = db.StoreMediaInfo("msg1", "123@s.whatsapp.net", "http://example.com", []byte("key"), []byte("sha"), []byte("encsha"), 123)
	assert.NoError(t, err)

	mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength, err := db.GetMediaInfo("msg1", "123@s.whatsapp.net")
	assert.NoError(t, err)
	assert.Equal(t, "text", mediaType)
	assert.Equal(t, "", filename)
	assert.Equal(t, "http://example.com", url)
	assert.Equal(t, []byte("key"), mediaKey)
	assert.Equal(t, []byte("sha"), fileSHA256)
	assert.Equal(t, []byte("encsha"), fileEncSHA256)
	assert.Equal(t, uint64(123), fileLength)

	// Test GetMessageMediaTypeAndFilename
	mediaType, filename, err = db.GetMessageMediaTypeAndFilename("msg1", "123@s.whatsapp.net")
	assert.NoError(t, err)
	assert.Equal(t, "text", mediaType)
	assert.Equal(t, "", filename)
}