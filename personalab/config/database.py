"""
Database configuration module for PersonaLab.

Supports both SQLite and PostgreSQL backends with automatic detection and fallback.
"""

import os
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass


DatabaseBackend = Literal["sqlite", "postgresql"]


@dataclass
class DatabaseConfig:
    """Database configuration data class."""
    backend: DatabaseBackend
    connection_params: Dict[str, Any]
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.backend not in ["sqlite", "postgresql"]:
            raise ValueError(f"Unsupported database backend: {self.backend}")
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create database config from environment variables."""
        # Check if PostgreSQL is configured
        postgres_host = os.getenv('POSTGRES_HOST')
        postgres_db = os.getenv('POSTGRES_DB')
        postgres_user = os.getenv('POSTGRES_USER')
        postgres_password = os.getenv('POSTGRES_PASSWORD')
        
        # If PostgreSQL environment variables are set, use PostgreSQL
        if postgres_host and postgres_db:
            # Auto-detect user if not specified
            if not postgres_user:
                import getpass
                postgres_user = getpass.getuser()
            
            # Use empty password if not specified (for local development)
            if postgres_password is None:
                postgres_password = ""
                
            return cls(
                backend="postgresql",
                connection_params={
                    'host': postgres_host,
                    'port': os.getenv('POSTGRES_PORT', '5432'),
                    'dbname': postgres_db,
                    'user': postgres_user,
                    'password': postgres_password
                }
            )
        
        # Default to SQLite
        return cls(
            backend="sqlite",
            connection_params={
                'memory_db_path': os.getenv('MEMORY_DB_PATH', 'memory.db'),
                'conversation_db_path': os.getenv('CONVERSATION_DB_PATH', 'conversations.db')
            }
        )
    
    @classmethod
    def create_sqlite(
        cls, 
        memory_db_path: str = "memory.db", 
        conversation_db_path: str = "conversations.db"
    ) -> "DatabaseConfig":
        """Create SQLite database configuration."""
        return cls(
            backend="sqlite",
            connection_params={
                'memory_db_path': memory_db_path,
                'conversation_db_path': conversation_db_path
            }
        )
    
    @classmethod
    def create_postgresql(
        cls,
        host: str = "localhost",
        port: str = "5432",
        dbname: str = "personalab",
        user: Optional[str] = None,
        password: str = "",
        connection_string: Optional[str] = None
    ) -> "DatabaseConfig":
        """Create PostgreSQL database configuration."""
        if connection_string:
            return cls(
                backend="postgresql",
                connection_params={'connection_string': connection_string}
            )
        
        # Auto-detect user if not provided (useful for macOS Homebrew PostgreSQL)
        if user is None:
            import getpass
            user = getpass.getuser()
        
        return cls(
            backend="postgresql",
            connection_params={
                'host': host,
                'port': port,
                'dbname': dbname,
                'user': user,
                'password': password
            }
        )


class DatabaseManager:
    """
    Database manager that provides unified interface for different database backends.
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
        """Get memory database instance based on configured backend."""
        if self._memory_db is None:
            if self.config.backend == "postgresql":
                from ..memory.pg_storage import PostgreSQLMemoryDB
                self._memory_db = PostgreSQLMemoryDB(**self.config.connection_params)
            else:
                from ..memory.storage import MemoryDB
                self._memory_db = MemoryDB(self.config.connection_params.get('memory_db_path', 'memory.db'))
        
        return self._memory_db
    
    def get_conversation_db(self):
        """Get conversation database instance based on configured backend."""
        if self._conversation_db is None:
            if self.config.backend == "postgresql":
                from ..memo.pg_storage import PostgreSQLConversationDB
                self._conversation_db = PostgreSQLConversationDB(**self.config.connection_params)
            else:
                from ..memo.storage import ConversationDB
                self._conversation_db = ConversationDB(self.config.connection_params.get('conversation_db_path', 'conversations.db'))
        
        return self._conversation_db
    
    def test_connection(self) -> bool:
        """Test database connections for both memory and conversation databases."""
        try:
            memory_db = self.get_memory_db()
            conversation_db = self.get_conversation_db()
            
            # Test both connections
            if hasattr(memory_db, '_test_connection'):
                memory_db._test_connection()
            if hasattr(conversation_db, '_test_connection'):
                conversation_db._test_connection()
            
            return True
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the current database backend."""
        return {
            'backend': self.config.backend,
            'connection_params': {
                k: v for k, v in self.config.connection_params.items() 
                if k not in ['password']  # Hide password for security
            }
        }
    
    def close(self):
        """Close database connections."""
        if self._memory_db and hasattr(self._memory_db, 'close'):
            self._memory_db.close()
        if self._conversation_db and hasattr(self._conversation_db, 'close'):
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


def configure_database(backend: DatabaseBackend, **kwargs) -> DatabaseManager:
    """
    Configure database backend globally.
    
    Args:
        backend: Database backend type
        **kwargs: Backend-specific configuration parameters
        
    Returns:
        DatabaseManager: Configured database manager
    """
    if backend == "postgresql":
        config = DatabaseConfig.create_postgresql(**kwargs)
    elif backend == "sqlite":
        config = DatabaseConfig.create_sqlite(**kwargs)
    else:
        raise ValueError(f"Unsupported database backend: {backend}")
    
    return get_database_manager(config)


def setup_postgresql(
    host: str = "localhost",
    port: str = "5432", 
    dbname: str = "personalab",
    user: Optional[str] = None,
    password: str = "",
    connection_string: Optional[str] = None
) -> DatabaseManager:
    """
    Setup PostgreSQL as the database backend.
    
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
        "postgresql",
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connection_string=connection_string
    )


def setup_sqlite(
    memory_db_path: str = "memory.db",
    conversation_db_path: str = "conversations.db"
) -> DatabaseManager:
    """
    Setup SQLite as the database backend.
    
    Args:
        memory_db_path: Path to memory database file
        conversation_db_path: Path to conversation database file
        
    Returns:
        DatabaseManager: Configured database manager
    """
    return configure_database(
        "sqlite",
        memory_db_path=memory_db_path,
        conversation_db_path=conversation_db_path
    ) 