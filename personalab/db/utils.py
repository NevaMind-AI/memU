"""
Database utility functions for PersonaLab.

Provides common database operations, connection management, and error handling.
"""

import functools
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Tuple, TypeVar, Callable

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def build_connection_string(**kwargs: str) -> str:
    """
    Build PostgreSQL connection string from parameters or environment variables.
    
    This function creates a properly formatted PostgreSQL connection string using
    provided parameters or falling back to environment variables.
    
    Args:
        **kwargs: Database connection parameters including:
            - host (str): Database host address
            - port (str): Database port number
            - dbname (str): Database name
            - user (str): Database username
            - password (str): Database password
        
    Returns:
        str: Formatted PostgreSQL connection string in the format:
            postgresql://user:password@host:port/dbname
        
    Raises:
        ValueError: If required parameters (host, dbname) are missing
        
    Example:
        >>> build_connection_string(host="localhost", dbname="mydb", user="admin")
        'postgresql://admin:@localhost:5432/mydb'
    """
    params = {
        "host": kwargs.get("host", os.getenv("POSTGRES_HOST", "localhost")),
        "port": kwargs.get("port", os.getenv("POSTGRES_PORT", "5432")),
        "dbname": kwargs.get("dbname", os.getenv("POSTGRES_DB", "personalab")),
        "user": kwargs.get("user", os.getenv("POSTGRES_USER", "postgres")),
        "password": kwargs.get("password", os.getenv("POSTGRES_PASSWORD", "")),
    }
    
    # Validate required parameters
    if not params["host"] or not params["dbname"]:
        raise ValueError(
            "Database host and dbname are required. "
            "Set POSTGRES_HOST and POSTGRES_DB environment variables."
        )
    
    connection_string = (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )
    
    logger.debug(f"Built connection string for {params['user']}@{params['host']}:{params['port']}/{params['dbname']}")
    return connection_string


def test_database_connection(connection_string: str) -> bool:
    """
    Test database connection.
    
    Args:
        connection_string: PostgreSQL connection string
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                logger.debug("Database connection test successful")
                return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


@contextmanager
def get_db_connection(connection_string: str) -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for database connections.
    
    Args:
        connection_string: PostgreSQL connection string
        
    Yields:
        psycopg2.extensions.connection: Database connection
        
    Raises:
        ConnectionError: If connection fails
    """
    conn = None
    try:
        conn = psycopg2.connect(connection_string)
        logger.debug("Database connection established")
        yield conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        if conn:
            conn.rollback()
        raise ConnectionError(f"Failed to connect to database: {e}")
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


@contextmanager
def get_db_cursor(
    connection_string: str,
    cursor_factory: Optional[type] = None
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """
    Context manager for database cursors.
    
    Args:
        connection_string: PostgreSQL connection string
        cursor_factory: Cursor factory class (e.g., RealDictCursor)
        
    Yields:
        psycopg2.extensions.cursor: Database cursor
    """
    with get_db_connection(connection_string) as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()


def database_operation(
    connection_string: str,
    use_dict_cursor: bool = False
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    Decorator for database operations with automatic error handling.
    
    Args:
        connection_string: PostgreSQL connection string
        use_dict_cursor: Whether to use DictCursor for results
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            cursor_factory = psycopg2.extras.RealDictCursor if use_dict_cursor else None
            
            try:
                with get_db_cursor(connection_string, cursor_factory) as cursor:
                    return func(cursor, *args, **kwargs)
            except Exception as e:
                logger.error(f"Database operation '{func.__name__}' failed: {e}")
                return None
                
        return wrapper
    return decorator


def safe_database_operation(
    operation_name: str,
    default_return: T = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for safe database operations with custom error handling.
    
    Args:
        operation_name: Name of the operation for logging
        default_return: Default return value on error
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Database operation '{operation_name}' completed successfully")
                return result
            except Exception as e:
                logger.error(f"Database operation '{operation_name}' failed: {e}")
                return default_return
                
        return wrapper
    return decorator


def get_database_info(connection_string: str) -> Dict[str, Any]:
    """
    Get database information and statistics.
    
    Args:
        connection_string: PostgreSQL connection string
        
    Returns:
        Dict[str, Any]: Database information
    """
    try:
        with get_db_cursor(connection_string, psycopg2.extras.RealDictCursor) as cursor:
            # Get database version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()["version"]
            
            # Check pgvector extension
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            has_pgvector = cursor.fetchone()["exists"]
            
            # Get database size
            cursor.execute(
                "SELECT pg_size_pretty(pg_database_size(current_database())) as size"
            )
            size = cursor.fetchone()["size"]
            
            return {
                "version": version,
                "has_pgvector": has_pgvector,
                "size": size,
                "connection_status": "connected"
            }
            
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "connection_status": "failed",
            "error": str(e)
        }


def ensure_pgvector_extension(connection_string: str) -> bool:
    """
    Ensure pgvector extension is installed and enabled.
    
    Args:
        connection_string: PostgreSQL connection string
        
    Returns:
        bool: True if pgvector is available, False otherwise
    """
    try:
        with get_db_cursor(connection_string) as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("pgvector extension ensured")
            return True
    except Exception as e:
        logger.error(f"Failed to ensure pgvector extension: {e}")
        return False 