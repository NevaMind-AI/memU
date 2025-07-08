"""
PersonaLab Database Module

Centralized database management:
- PostgreSQL storage implementations with pgvector support
- Database configuration and connection management
"""

from .config import (
    DatabaseConfig,
    DatabaseManager,
    get_database_manager,
    setup_postgresql,
)
from .pg_storage import PostgreSQLMemoryDB, PostgreSQLConversationDB, PostgreSQLStorageBase

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
] 