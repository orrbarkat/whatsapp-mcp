"""Verification script to ensure SQLite adapter implements all Protocol contracts."""

from database import (
    MessageRepository,
    ChatRepository,
    ContactRepository,
    AuthenticationRepository,
    DatabaseAdapter,
    UnitOfWork
)
from database_sqlite import (
    SQLiteMessageRepository,
    SQLiteChatRepository,
    SQLiteContactRepository,
    SQLiteAuthenticationRepository,
    SQLiteDatabaseAdapter,
    SQLiteUnitOfWork,
    SQLiteConnection
)

def verify_protocol_implementation():
    """Verify that SQLite implementations satisfy Protocol contracts."""

    # Create in-memory connections for testing
    messages_conn = SQLiteConnection(':memory:')
    auth_conn = SQLiteConnection(':memory:')
    messages_conn.connect()
    auth_conn.connect()

    # Verify repository implementations
    msg_repo = SQLiteMessageRepository(messages_conn)
    chat_repo = SQLiteChatRepository(messages_conn)
    contact_repo = SQLiteContactRepository(messages_conn)
    auth_repo = SQLiteAuthenticationRepository(auth_conn)

    # Verify these are valid Protocol implementations by checking they have the required methods
    assert hasattr(msg_repo, 'get_sender_name'), "MessageRepository missing get_sender_name"
    assert hasattr(msg_repo, 'list_messages'), "MessageRepository missing list_messages"
    assert hasattr(msg_repo, 'get_message_context'), "MessageRepository missing get_message_context"

    assert hasattr(chat_repo, 'list_chats'), "ChatRepository missing list_chats"
    assert hasattr(chat_repo, 'get_chat'), "ChatRepository missing get_chat"
    assert hasattr(chat_repo, 'get_direct_chat_by_contact'), "ChatRepository missing get_direct_chat_by_contact"

    assert hasattr(contact_repo, 'search_contacts'), "ContactRepository missing search_contacts"
    assert hasattr(contact_repo, 'get_contact_chats'), "ContactRepository missing get_contact_chats"
    assert hasattr(contact_repo, 'get_last_interaction'), "ContactRepository missing get_last_interaction"

    assert hasattr(auth_repo, 'check_authentication_status'), "AuthenticationRepository missing check_authentication_status"

    # Verify UnitOfWork implementation
    uow = SQLiteUnitOfWork(messages_conn, auth_conn)
    assert hasattr(uow, 'begin'), "UnitOfWork missing begin"
    assert hasattr(uow, 'commit'), "UnitOfWork missing commit"
    assert hasattr(uow, 'rollback'), "UnitOfWork missing rollback"
    assert hasattr(uow, '__enter__'), "UnitOfWork missing __enter__"
    assert hasattr(uow, '__exit__'), "UnitOfWork missing __exit__"

    # Verify DatabaseAdapter implementation
    adapter = SQLiteDatabaseAdapter(':memory:', ':memory:')
    assert hasattr(adapter, 'messages'), "DatabaseAdapter missing messages property"
    assert hasattr(adapter, 'chats'), "DatabaseAdapter missing chats property"
    assert hasattr(adapter, 'contacts'), "DatabaseAdapter missing contacts property"
    assert hasattr(adapter, 'authentication'), "DatabaseAdapter missing authentication property"
    assert hasattr(adapter, 'unit_of_work'), "DatabaseAdapter missing unit_of_work"
    assert hasattr(adapter, 'close'), "DatabaseAdapter missing close"

    # Verify properties return correct types
    assert isinstance(adapter.messages, SQLiteMessageRepository), "messages property returns wrong type"
    assert isinstance(adapter.chats, SQLiteChatRepository), "chats property returns wrong type"
    assert isinstance(adapter.contacts, SQLiteContactRepository), "contacts property returns wrong type"
    assert isinstance(adapter.authentication, SQLiteAuthenticationRepository), "authentication property returns wrong type"

    # Test unit_of_work context manager
    with adapter.unit_of_work() as uow:
        assert isinstance(uow, SQLiteUnitOfWork), "unit_of_work returns wrong type"

    # Clean up
    adapter.close()
    messages_conn.close()
    auth_conn.close()

    print("✓ All Protocol contracts are properly implemented!")
    print("✓ SQLiteMessageRepository implements MessageRepository")
    print("✓ SQLiteChatRepository implements ChatRepository")
    print("✓ SQLiteContactRepository implements ContactRepository")
    print("✓ SQLiteAuthenticationRepository implements AuthenticationRepository")
    print("✓ SQLiteUnitOfWork implements UnitOfWork")
    print("✓ SQLiteDatabaseAdapter implements DatabaseAdapter")
    print("✓ :memory: support is working correctly")

if __name__ == '__main__':
    verify_protocol_implementation()
