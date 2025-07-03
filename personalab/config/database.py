"""
Database configuration module for PersonaLab.

Supports PostgreSQL backend with pgvector extension for vector operations.
"""

import getpass
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

DatabaseBackend = "postgresql"


@dataclass
class DatabaseConfig:
    """Database configuration data class for PostgreSQL."""

    backend: str = "postgresql"
    connection_params: Dict[str, Any] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.backend != "postgresql":
            raise ValueError(
                f"Only PostgreSQL backend is supported, got: {self.backend}"
            )
        if self.connection_params is None:
            self.connection_params = {}

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create database config from environment variables."""
        # Check if PostgreSQL is configured
        postgres_host = os.getenv("POSTGRES_HOST")
        postgres_db = os.getenv("POSTGRES_DB")
        postgres_user = os.getenv("POSTGRES_USER")
        postgres_password = os.getenv("POSTGRES_PASSWORD")

        # PostgreSQL is required
        if not postgres_host or not postgres_db:
            raise ValueError(
                "PostgreSQL configuration is required. Please set POSTGRES_HOST and POSTGRES_DB environment variables. "
                "For setup instructions, see: docs/POSTGRESQL_SETUP.md"
            )

        # Auto-detect user if not specified
        if not postgres_user:
            postgres_user = getpass.getuser()

        # Use empty password if not specified (for local development)
        if postgres_password is None:
            postgres_password = ""

        return cls(
            backend="postgresql",
            connection_params={
                "host": postgres_host,
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "dbname": postgres_db,
                "user": postgres_user,
                "password": postgres_password,
            },
        )

    @classmethod
    def create_postgresql(
        cls,
        host: str = "localhost",
        port: str = "5432",
        dbname: str = "personalab",
        user: Optional[str] = None,
        password: str = "",
        connection_string: Optional[str] = None,
    ) -> "DatabaseConfig":
        """Create PostgreSQL database configuration."""
        if connection_string:
            return cls(
                backend="postgresql",
                connection_params={"connection_string": connection_string},
            )

        # Auto-detect user if not provided (useful for macOS Homebrew PostgreSQL)
        if user is None:
            user = getpass.getuser()

        return cls(
            backend="postgresql",
            connection_params={
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
                "password": password,
            },
        )


class DatabaseManager:
    """
    Database manager that provides unified interface for PostgreSQL backend with pgvector.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager.

        Args:
            config: Database configuration. If None, will be created from environment.
        """
        self.config = config or DatabaseConfig.from_env()
        self._memory_db = None
        self._conversation_db = None

    def get_memory_db(self):
        """Get PostgreSQL memory database instance with pgvector support."""
        if self._memory_db is None:
            # Import here to avoid circular imports
            from ..memory.pg_storage import PostgreSQLMemoryDB

            self._memory_db = PostgreSQLMemoryDB(**self.config.connection_params)
        return self._memory_db

    def get_conversation_db(self):
        """Get PostgreSQL conversation database instance with pgvector support."""
        if self._conversation_db is None:
            # Import here to avoid circular imports
            from ..memo.pg_storage import PostgreSQLConversationDB

            self._conversation_db = PostgreSQLConversationDB(
                **self.config.connection_params
            )
        return self._conversation_db

    def test_connection(self) -> bool:
        """Test database connections for both memory and conversation databases."""
        try:
            memory_db = self.get_memory_db()
            conversation_db = self.get_conversation_db()

            # Test both connections
            if hasattr(memory_db, "_test_connection"):
                memory_db._test_connection()
            if hasattr(conversation_db, "_test_connection"):
                conversation_db._test_connection()

            return True
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False

    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the current database backend."""
        return {
            "backend": self.config.backend,
            "connection_params": {
                k: v
                for k, v in self.config.connection_params.items()
                if k not in ["password"]  # Hide password for security
            },
        }

    def close(self):
        """Close database connections."""
        if self._memory_db and hasattr(self._memory_db, "close"):
            self._memory_db.close()
        if self._conversation_db and hasattr(self._conversation_db, "close"):
            self._conversation_db.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """
    Get global database manager instance.

    Args:
        config: Database configuration. If None, will use environment-based config.

    Returns:
        DatabaseManager: Global database manager instance
    """
    global _db_manager

    if _db_manager is None or (config is not None):
        _db_manager = DatabaseManager(config)

    return _db_manager


def configure_database(**kwargs) -> DatabaseManager:
    """
    Configure PostgreSQL database backend globally.

    Args:
        **kwargs: PostgreSQL configuration parameters

    Returns:
        DatabaseManager: Configured database manager
    """
    config = DatabaseConfig.create_postgresql(**kwargs)
    return get_database_manager(config)


def setup_postgresql(
    host: str = "localhost",
    port: str = "5432",
    dbname: str = "personalab",
    user: Optional[str] = None,
    password: str = "",
    connection_string: Optional[str] = None,
) -> DatabaseManager:
    """
    Setup PostgreSQL as the database backend with pgvector support.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password
        connection_string: Direct connection string (overrides other params)

    Returns:
        DatabaseManager: Configured database manager
    """
    return configure_database(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connection_string=connection_string,
    )
