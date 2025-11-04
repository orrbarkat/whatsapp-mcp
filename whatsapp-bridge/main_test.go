package main

import (
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"google.golang.org/protobuf/proto"
)

func TestNewMessageStore(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	mock.ExpectExec("CREATE TABLE IF NOT EXISTS chats").WillReturnResult(sqlmock.NewResult(1, 1))

	store, err := NewMessageStore(db)
	require.NoError(t, err)
	assert.NotNil(t, store)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestStoreChat(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := &MessageStore{db: db}
	mock.ExpectExec("INSERT OR REPLACE INTO chats").
		WithArgs("jid", "name", sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))

	err = store.StoreChat("jid", "name", time.Now())
	require.NoError(t, err)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestStoreMessage(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := &MessageStore{db: db}
	mock.ExpectExec("INSERT OR REPLACE INTO messages").
		WithArgs("id", "chatJID", "sender", "content", sqlmock.AnyArg(), false, "mediaType", "filename", "url", []byte("mediaKey"), []byte("fileSHA256"), []byte("fileEncSHA256"), uint64(123)).
		WillReturnResult(sqlmock.NewResult(1, 1))

	err = store.StoreMessage("id", "chatJID", "sender", "content", time.Now(), false, "mediaType", "filename", "url", []byte("mediaKey"), []byte("fileSHA256"), []byte("fileEncSHA256"), uint64(123))
	require.NoError(t, err)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestGetMessages(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := &MessageStore{db: db}
	rows := sqlmock.NewRows([]string{"sender", "content", "timestamp", "is_from_me", "media_type", "filename"}).
		AddRow("sender", "content", time.Now(), false, "mediaType", "filename")

	mock.ExpectQuery("SELECT sender, content, timestamp, is_from_me, media_type, filename FROM messages").
		WithArgs("chatJID", 10).
		WillReturnRows(rows)

	messages, err := store.GetMessages("chatJID", 10)
	require.NoError(t, err)
	assert.Len(t, messages, 1)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestGetChats(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := &MessageStore{db: db}
	rows := sqlmock.NewRows([]string{"jid", "last_message_time"}).
		AddRow("jid", time.Now())

	mock.ExpectQuery("SELECT jid, last_message_time FROM chats").
		WillReturnRows(rows)

	chats, err := store.GetChats()
	require.NoError(t, err)
	assert.Len(t, chats, 1)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestExtractTextContent(t *testing.T) {
	// Test with conversation text
	msg1 := &waProto.Message{Conversation: proto.String("Hello")}
	assert.Equal(t, "Hello", extractTextContent(msg1))

	// Test with extended text message
	msg2 := &waProto.Message{ExtendedTextMessage: &waProto.ExtendedTextMessage{Text: proto.String("World")}}
	assert.Equal(t, "World", extractTextContent(msg2))

	// Test with no text
	msg3 := &waProto.Message{}
	assert.Equal(t, "", extractTextContent(msg3))

	// Test with nil message
	assert.Equal(t, "", extractTextContent(nil))
}

func TestExtractMediaInfo(t *testing.T) {
	// Test with image message
	imgMsg := &waProto.Message{ImageMessage: &waProto.ImageMessage{URL: proto.String("img_url")}}
	mediaType, _, url, _, _, _, _ := extractMediaInfo(imgMsg)
	assert.Equal(t, "image", mediaType)
	assert.Equal(t, "img_url", url)

	// Test with video message
	vidMsg := &waProto.Message{VideoMessage: &waProto.VideoMessage{URL: proto.String("vid_url")}}
	mediaType, _, url, _, _, _, _ = extractMediaInfo(vidMsg)
	assert.Equal(t, "video", mediaType)
	assert.Equal(t, "vid_url", url)

	// Test with audio message
	audMsg := &waProto.Message{AudioMessage: &waProto.AudioMessage{URL: proto.String("aud_url")}}
	mediaType, _, url, _, _, _, _ = extractMediaInfo(audMsg)
	assert.Equal(t, "audio", mediaType)
	assert.Equal(t, "aud_url", url)

	// Test with document message
	docMsg := &waProto.Message{DocumentMessage: &waProto.DocumentMessage{URL: proto.String("doc_url"), FileName: proto.String("doc.pdf")}}
	mediaType, filename, url, _, _, _, _ := extractMediaInfo(docMsg)
	assert.Equal(t, "document", mediaType)
	assert.Equal(t, "doc.pdf", filename)
	assert.Equal(t, "doc_url", url)

	// Test with no media
	noMediaMsg := &waProto.Message{}
	mediaType, _, _, _, _, _, _ = extractMediaInfo(noMediaMsg)
	assert.Equal(t, "", mediaType)

	// Test with nil message
	mediaType, _, _, _, _, _, _ = extractMediaInfo(nil)
	assert.Equal(t, "", mediaType)
}

func TestExtractDirectPathFromURL(t *testing.T) {
	url := "https://mmg.whatsapp.net/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc?ccb=11-4&oh=..."
	expected := "/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc"
	assert.Equal(t, expected, extractDirectPathFromURL(url))

	url = "invalid_url"
	assert.Equal(t, "invalid_url", extractDirectPathFromURL(url))
}
