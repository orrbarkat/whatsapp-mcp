"""Configuration management for database adapters.

This module handles configuration loading from environment variables and config files,
and provides factory functions to create appropriate database adapters.
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse
import yaml

from database import DatabaseAdapter
from database_sqlite import SQLiteDatabaseAdapter
from database_supabase import SupabaseDatabaseAdapter

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration for database connections."""

    def __init__(
        self,
        database_type: str,
        messages_db_path: Optional[str] = None,
        auth_db_path: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        """Initialize database configuration.

        Args:
            database_type: Type of database - 'sqlite', 'supabase', or 'postgres'
            messages_db_path: Path to SQLite messages database (for SQLite)
            auth_db_path: Path to SQLite auth database (for SQLite)
            supabase_url: Supabase project URL (for Supabase/Postgres)
            supabase_key: Supabase API key (for Supabase/Postgres)
        """
        self.database_type = database_type
        self.messages_db_path = messages_db_path
        self.auth_db_path = auth_db_path
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

    @classmethod
    def from_environment(cls) -> "DatabaseConfig":
        """Load configuration from environment variables and config files.

        Priority order:
        1. DATABASE_URL environment variable (highest priority)
        2. config.yaml file
        3. Default to in-memory SQLite (if nothing else is configured)

        Returns:
            DatabaseConfig instance with loaded configuration
        """
        # Try DATABASE_URL first
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            logger.info("Loading database configuration from DATABASE_URL environment variable")
            return cls._from_database_url(database_url)

        # Try config.yaml
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)

                if config_data and 'database' in config_data:
                    logger.info("Loading database configuration from config.yaml")
                    return cls._from_yaml_config(config_data['database'])
            except Exception as e:
                logger.warning(f"Failed to load config.yaml: {e}. Falling back to defaults.")

        # Default to in-memory SQLite
        logger.info("No configuration found. Defaulting to in-memory SQLite database")
        return cls(
            database_type='sqlite',
            messages_db_path=':memory:',
            auth_db_path=':memory:'
        )

    @classmethod
    def _from_database_url(cls, database_url: str) -> "DatabaseConfig":
        """Parse DATABASE_URL and create config.

        Args:
            database_url: Database connection URL

        Returns:
            DatabaseConfig instance

        Raises:
            ValueError: If URL format is invalid
        """
        try:
            parsed = urlparse(database_url)
            scheme = parsed.scheme.lower()

            if scheme == 'sqlite':
                # sqlite:///path/to/db.db or sqlite://:memory:
                db_path = parsed.path.lstrip('/') if parsed.path != '/:memory:' else ':memory:'
                if not db_path:
                    db_path = ':memory:'

                # For SQLite, we need both messages and auth DB paths
                # Use the same base path but different files
                if db_path == ':memory:':
                    messages_path = ':memory:'
                    auth_path = ':memory:'
                else:
                    base_dir = os.path.dirname(db_path)
                    messages_path = os.path.join(base_dir, 'messages.db')
                    auth_path = os.path.join(base_dir, 'whatsapp.db')

                return cls(
                    database_type='sqlite',
                    messages_db_path=messages_path,
                    auth_db_path=auth_path
                )

            elif scheme in ('postgresql', 'postgres'):
                # postgresql://user:pass@host:port/db
                # Convert to Supabase format (requires SUPABASE_URL and SUPABASE_KEY)
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

                if not supabase_url or not supabase_key:
                    raise ValueError(
                        "PostgreSQL connection requires SUPABASE_URL and SUPABASE_KEY "
                        "(or SUPABASE_ANON_KEY) environment variables"
                    )

                return cls(
                    database_type='postgres',
                    supabase_url=supabase_url,
                    supabase_key=supabase_key
                )

            else:
                raise ValueError(f"Unsupported database URL scheme: {scheme}")

        except Exception as e:
            logger.error(f"Error parsing DATABASE_URL: {e}")
            raise ValueError(f"Invalid DATABASE_URL format: {e}")

    @classmethod
    def _from_yaml_config(cls, config_dict: dict) -> "DatabaseConfig":
        """Create config from YAML configuration dictionary.

        Args:
            config_dict: Dictionary from config.yaml 'database' section

        Returns:
            DatabaseConfig instance
        """
        url = config_dict.get('url')

        if url:
            return cls._from_database_url(url)

        # Fallback to default in-memory SQLite
        logger.warning("No 'url' found in config.yaml database section. Using in-memory SQLite.")
        return cls(
            database_type='sqlite',
            messages_db_path=':memory:',
            auth_db_path=':memory:'
        )


def create_database_adapter(config: DatabaseConfig) -> DatabaseAdapter:
    """Create and return appropriate database adapter based on configuration.

    Args:
        config: DatabaseConfig instance

    Returns:
        DatabaseAdapter implementation (SQLiteDatabaseAdapter or SupabaseDatabaseAdapter)

    Raises:
        ValueError: If configuration is invalid or adapter cannot be created
    """
    try:
        if config.database_type == 'sqlite':
            logger.info(f"Creating SQLite database adapter (messages: {config.messages_db_path}, auth: {config.auth_db_path})")
            return SQLiteDatabaseAdapter(
                messages_db_path=config.messages_db_path,
                auth_db_path=config.auth_db_path
            )

        elif config.database_type in ('postgres', 'supabase'):
            logger.info(f"Creating Supabase database adapter (url: {config.supabase_url})")
            return SupabaseDatabaseAdapter(
                supabase_url=config.supabase_url,
                supabase_key=config.supabase_key
            )

        else:
            raise ValueError(f"Unsupported database type: {config.database_type}")

    except Exception as e:
        logger.error(f"Failed to create database adapter: {e}")
        raise ValueError(f"Could not create database adapter: {e}")


# Global adapter cache
_cached_adapter: Optional[DatabaseAdapter] = None


def get_database_adapter() -> DatabaseAdapter:
    """Get or create the global database adapter instance.

    This function lazily creates and caches the database adapter on first call.
    Subsequent calls return the cached instance.

    Returns:
        DatabaseAdapter instance

    Raises:
        ValueError: If adapter creation fails
    """
    global _cached_adapter

    if _cached_adapter is None:
        try:
            config = DatabaseConfig.from_environment()
            _cached_adapter = create_database_adapter(config)
            logger.info("Database adapter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database adapter: {e}")
            raise

    return _cached_adapter
