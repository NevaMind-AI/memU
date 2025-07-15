"""
MemU Database Module

Centralized database management:
- PostgreSQL storage implementations with pgvector support
- Database configuration and connection management
- Database utility functions and helpers
"""

from .config import (
    DatabaseConfig,
    DatabaseManager,
    get_database_manager,
    setup_postgresql,
)
from .pg_storage import PostgreSQLMemoryDB, PostgreSQLConversationDB, PostgreSQLStorageBase
from .utils import (
    build_connection_string,
    test_database_connection,
    get_db_connection,
    get_db_cursor,
    get_database_info,
    ensure_pgvector_extension,
)

__all__ = [
    # Storage implementations
    "PostgreSQLMemoryDB",
    "PostgreSQLConversationDB", 
    "PostgreSQLStorageBase",
    # Configuration and management
    "DatabaseConfig",
    "DatabaseManager",
    "get_database_manager",
    "setup_postgresql",
    # Database utilities
    "build_connection_string",
    "test_database_connection",
    "get_db_connection",
    "get_db_cursor",
    "get_database_info",
    "ensure_pgvector_extension",
] 