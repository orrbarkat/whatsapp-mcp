"""
Pytest fixtures for WhatsApp MCP server tests.
"""
import pytest
import os
import importlib
from .test_utils import temp_test_db

@pytest.fixture
def test_db():
    """Provide a temporary test database for tests."""
    with temp_test_db() as db_path:
        # Set the environment variable so the whatsapp module uses our test DB
        original_db_path = os.environ.get("MESSAGES_DB_PATH")
        os.environ["MESSAGES_DB_PATH"] = db_path
        
        try:
            yield db_path
        finally:
            # Restore original DB path
            if original_db_path is not None:
                os.environ["MESSAGES_DB_PATH"] = original_db_path
            elif "MESSAGES_DB_PATH" in os.environ:
                del os.environ["MESSAGES_DB_PATH"]

@pytest.fixture
def test_db_with_reload(test_db):
    """Provide a test database and reload the whatsapp module to pick up the new path."""
    import whatsapp
    importlib.reload(whatsapp)
    yield test_db
    # The whatsapp module will be reloaded for the next test automatically
