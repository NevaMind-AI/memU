"""
PostgreSQL storage layer for MemU.

Implements PostgreSQL + pgvector storage for:
- Memory objects (profiles, events, mind analysis)
- Conversation objects (conversations and messages)

All classes use the same PostgreSQL database with pgvector extension for semantic search.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool
from pgvector.psycopg2 import register_vector

from ..memory.base import EventMemory, Memory, ProfileMemory
# from ..memo.models import Conversation, ConversationMessage  # Removed memo module
from ..utils import get_logger
from .utils import build_connection_string, test_database_connection, ensure_pgvector_extension

logger = get_logger(__name__)


def retry_on_table_missing(max_retries: int = 1):
    """
    Decorator to retry database operations when tables are missing.
    
    Args:
        max_retries: Maximum number of retries after the initial attempt
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except psycopg2.errors.UndefinedTable:
                logger.warning(f"Database tables missing in {func.__name__} - reinitializing and retrying")
                self._init_database()
                # Retry the operation once after re-initialization
                for attempt in range(max_retries):
                    try:
                        return func(self, *args, **kwargs)
                    except psycopg2.errors.UndefinedTable:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Retry {attempt + 1} failed in {func.__name__}, trying again")
                        continue
            except Exception:
                raise
        return wrapper
    return decorator


class PostgreSQLStorageBase:
    """
    Base class for PostgreSQL storage operations.
    
    Provides common functionality for database connection, initialization,
    and utility methods shared by Memory and Conversation storage.
    """
    
    # Class-level connection pool shared across all instances
    _connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

    def __init__(self, connection_string: Optional[str] = None, **kwargs):
        """
        Initialize PostgreSQL database connection.

        Args:
            connection_string: PostgreSQL connection string
            **kwargs: Connection parameters (host, port, dbname, user, password)
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            # Build connection string from parameters or environment variables
            self.connection_string = build_connection_string(**kwargs)

        # Initialize connection pool if not already created
        if PostgreSQLStorageBase._connection_pool is None:
            self._init_connection_pool()
            
        self._test_connection()
        self._init_database()
        
    def _init_connection_pool(self):
        """Initialize the connection pool."""
        try:
            PostgreSQLStorageBase._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=self.connection_string
            )
            logger.info("Connection pool initialized with 2-10 connections")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
            
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            conn = PostgreSQLStorageBase._connection_pool.getconn()
            # Register pgvector for this connection
            register_vector(conn)
            yield conn
        finally:
            if conn:
                PostgreSQLStorageBase._connection_pool.putconn(conn)

    def _test_connection(self) -> None:
        """Test database connection."""
        if not test_database_connection(self.connection_string):
            raise ConnectionError("Failed to connect to PostgreSQL database")
        logger.debug("Database connection test successful")

    def _init_database(self) -> None:
        """Initialize database with pgvector extension and create tables."""
        try:
            # Ensure pgvector extension
            if not ensure_pgvector_extension(self.connection_string):
                logger.warning("pgvector extension may not be available")
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Create tables specific to this storage type
                    self._init_tables(cur)
                    conn.commit()
                    
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _init_tables(self, cur):
        """Initialize tables specific to the storage type. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _init_tables")

    def _calculate_hash(self, content: str) -> str:
        """Calculate content hash."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def close(self):
        """Close database connection (PostgreSQL handles connection pooling)."""
        pass


class PostgreSQLMemoryDB(PostgreSQLStorageBase):
    """
    PostgreSQL Memory database operations repository.

    Provides complete database storage and management functionality for Memory objects
    using PostgreSQL with pgvector extension for vector storage.
    """

    def _init_tables(self, cur):
        """Initialize unified memory table."""
        # Create unified memories table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                category TEXT,
                content TEXT,
                embedding vector(1536),  -- Default OpenAI embedding dimension
                links JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                happened_at TIMESTAMP
            )
        """
        )

        # Create memory history table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_history (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                section TEXT,
                content TEXT,
                links JSONB
            )
        """
        )

        # Create conversations table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                status TEXT DEFAULT 'active',
                metadata JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP
            )
        """
        )

        # Create indexes for better performance
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_agent_user ON memories(agent_id, user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_happened_at ON memories(happened_at)"
        )

        # Create vector similarity search index using HNSW
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_vector_hnsw
            ON memories USING hnsw (embedding vector_cosine_ops)
        """
        )
        
        # JSONB indexes for links
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_links_gin ON memories USING gin (links)"
        )
        
        # Add composite indexes for common memory query patterns
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_agent_user_category
            ON memories (agent_id, user_id, category)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_category_happened
            ON memories (category, happened_at)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_embedding_filtered
            ON memories (category) 
            WHERE embedding IS NOT NULL
        """
        )

        # Create indexes for memory_history table
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_memory_id ON memory_history(memory_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_agent_id ON memory_history(agent_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_user_id ON memory_history(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_action ON memory_history(action)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_timestamp ON memory_history(timestamp)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_section ON memory_history(section)"
        )

        # JSONB indexes for history links
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_history_links_gin ON memory_history USING gin (links)"
        )

        # Composite indexes for history queries
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_history_memory_timestamp
            ON memory_history (memory_id, timestamp DESC)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_history_agent_user_timestamp
            ON memory_history (agent_id, user_id, timestamp DESC)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_history_action_timestamp
            ON memory_history (action, timestamp DESC)
        """
        )

        # Create indexes for conversations table
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_agent_user ON conversations(agent_id, user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_ended_at ON conversations(ended_at)"
        )

        # JSONB indexes for conversation metadata
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_metadata_gin ON conversations USING gin (metadata)"
        )

        # Composite indexes for conversation queries
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_agent_user_status
            ON conversations (agent_id, user_id, status)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_status_updated
            ON conversations (status, updated_at DESC)
        """
        )

    @retry_on_table_missing()
    def save_memory_content(self, agent_id: str, user_id: str, category: str = None, content: str = None, links: dict = None, happened_at: datetime = None) -> str:
        """
        Save memory content to unified memories table.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Optional category for organization
            content: The actual content text
            links: Optional links/references in dict format
            happened_at: Optional timestamp when the event happened

        Returns:
            str: The memory ID if successful, None if failed
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Insert memory content
                    memory_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO memories
                        (id, agent_id, user_id, category, content, links, 
                         created_at, updated_at, happened_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            memory_id,
                            agent_id,
                            user_id,
                            category,
                            content,
                            json.dumps(links) if links else None,
                            datetime.now(),
                            datetime.now(),
                            happened_at
                        ),
                    )
                    
                    # Log the CREATE action to history
                    self._log_history_action(
                        cur, memory_id, agent_id, user_id, "CREATE", 
                        section="full", content=content, links=links
                    )
                    
                    conn.commit()
            return memory_id
        except Exception as e:
            logger.error(f"Error saving memory content: {e}")
            return None

    def _log_history_action(self, cur, memory_id: str, agent_id: str, user_id: str, action: str,
                           section: str = None, content: str = None, links: dict = None):
        """
        Internal method to log history action within existing transaction.
        
        Args:
            cur: Database cursor (must be within a transaction)
            memory_id: ID of the memory that was acted upon
            agent_id: Agent identifier
            user_id: User identifier
            action: Action type (CREATE, UPDATE, DELETE, READ, SEARCH, EMBED)
            section: Section that was affected
            content: Content involved in the action
            links: Links data involved in the action
        """
        try:
            history_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO memory_history
                (id, memory_id, agent_id, user_id, action, timestamp, section, content, links)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    history_id,
                    memory_id,
                    agent_id,
                    user_id,
                    action,
                    datetime.now(),
                    section,
                    content,
                    json.dumps(links) if links else None
                )
            )
        except Exception as e:
            logger.warning(f"Failed to log history action: {e}")
            # Don't fail the main operation if history logging fails

    @retry_on_table_missing()
    def save_memory(self, memory: Memory) -> bool:
        """
        Save complete Memory object to database.
        
        Legacy method that adapts to new unified table structure.

        Args:
            memory: Memory object

        Returns:
            bool: Whether save was successful
        """
        try:
            # Extract content from memory object and save each type
            profile_content = memory.get_profile()
            if profile_content:
                self.save_memory_content(
                    memory.agent_id, memory.user_id, 'profile', 
                    '\n'.join(profile_content), 'personal'
                )

            event_content = memory.get_events()
            if event_content:
                self.save_memory_content(
                    memory.agent_id, memory.user_id, 'event', 
                    '\n'.join(event_content), 'daily'
                )

            return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False

    @retry_on_table_missing()
    def get_memory_content(self, agent_id: str, user_id: str, category: str = None) -> List[Dict]:
        """
        Get memory content from unified memories table.

        Args:
            agent_id: Agent identifier
            user_id: User identifier 
            category: Optional category filter

        Returns:
            List[Dict]: List of memory records
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if category:
                        cur.execute(
                            """
                            SELECT id, agent_id, user_id, category, content, links, 
                                   created_at, updated_at, happened_at
                            FROM memories 
                            WHERE agent_id = %s AND user_id = %s AND category = %s
                            ORDER BY updated_at DESC
                            """,
                            (agent_id, user_id, category)
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, agent_id, user_id, category, content, links,
                                   created_at, updated_at, happened_at
                            FROM memories 
                            WHERE agent_id = %s AND user_id = %s
                            ORDER BY category, updated_at DESC
                            """,
                            (agent_id, user_id)
                        )
                    
                    results = cur.fetchall()
                    return [dict(row) for row in results]
                    
        except Exception as e:
            logger.error(f"Error getting memory content: {e}")
            return []

    def load_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Load complete Memory object from unified table.

        Args:
            memory_id: Memory ID

        Returns:
            Optional[Memory]: Memory object, returns None if not exists
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Load specific memory record
                    cur.execute(
                        "SELECT * FROM memories WHERE id = %s", (memory_id,)
                    )
                    memory_row = cur.fetchone()

                    if not memory_row:
                        return None

                    # Create Memory object with the specific content
                    memory = Memory(
                        agent_id=memory_row["agent_id"],
                        user_id=memory_row.get("user_id", "default_user"),
                        memory_client=None,  # No API client needed for database operations
                        memory_id=memory_id,
                    )
                    memory.created_at = memory_row["created_at"]
                    memory.updated_at = memory_row["updated_at"]

                    # Parse the content based on type
                    content_type = memory_row["category"] # Changed from content_type to category
                    content_text = memory_row["content"]
                    
                    if content_text:
                        content_list = [line.strip() for line in content_text.split('\n') if line.strip()]
                        
                        if content_type == 'profile':
                            memory.profile_memory = ProfileMemory(content_list)
                        elif content_type == 'event':
                            memory.event_memory = EventMemory(content_list)

                    return memory

        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return None

    def load_agent_memories(self, agent_id: str, user_id: str = "default") -> Optional[Memory]:
        """
        Load all memories for an agent-user combination and create a unified Memory object.

        Args:
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            Optional[Memory]: Combined Memory object with all content types
        """
        try:
            memories = self.get_memory_content(agent_id, user_id)
            if not memories:
                return None

            # Create a unified Memory object
            memory = Memory(
                agent_id=agent_id,
                user_id=user_id,
                memory_client=None,
                memory_id=str(uuid.uuid4()),  # Generate a new ID for the combined object
            )

            # Process each memory type
            for mem in memories:
                content_type = mem["category"] # Changed from content_type to category
                content_text = mem["content"]
                
                if content_text:
                    content_list = [line.strip() for line in content_text.split('\n') if line.strip()]
                    
                    if content_type == 'profile':
                        memory.profile_memory = ProfileMemory(content_list)
                    elif content_type == 'event':
                        memory.event_memory = EventMemory(content_list)

                # Use the most recent update time
                if mem["updated_at"] > memory.updated_at:
                    memory.updated_at = mem["updated_at"]

            return memory

        except Exception as e:
            logger.error(f"Error loading agent memories: {e}")
            return None

    def get_memory_by_agent(self, agent_id: str, user_id: str) -> Optional[Memory]:
        """
        Get Memory by agent_id and user_id.
        
        Design:
        - Query memories table by agent_id and user_id
        - Load content from memory_contents table

        Args:
            agent_id: Agent ID
            user_id: User ID

        Returns:
            Optional[Memory]: Memory object, returns None if not exists
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Find memory_id by agent_id and user_id
                    cur.execute(
                        "SELECT id FROM memories WHERE agent_id = %s AND user_id = %s",
                        (agent_id, user_id),
                    )
                    result = cur.fetchone()

                    if not result:
                        return None

                    # Load complete memory using memory_id
                    return self.load_memory(result["id"])

        except Exception as e:
            logger.error(f"Error getting memory by agent: {e}")
            return None

    def search_similar_memories(
        self,
        agent_id: str,
        query_vector: List[float],
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using vector similarity.

        Args:
            agent_id: Agent ID
            query_vector: Query vector for similarity search
            content_type: Content type filter (e.g., 'activity', 'profile', 'event', 'reminder', etc.)
            category: Category filter (e.g., 'personal', 'work', 'hobby', 'important')
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List[Dict]: List of similar memory content with metadata
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Base query for vector similarity search
                    query = """
                        SELECT 
                            id,
                            agent_id,
                            user_id,
                            category,
                            content,
                            created_at,
                            updated_at,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM memories
                        WHERE agent_id = %s
                        AND embedding IS NOT NULL
                    """

                    params = [str(query_vector), agent_id]

                    # Add content type filter if specified
                    if content_type:
                        query += " AND category = %s"
                        params.append(content_type)
                    
                    # Add category filter if specified
                    if category:
                        query += " AND category = %s"
                        params.append(category)

                    # Add similarity threshold and ordering
                    query += """
                        AND (1 - (embedding <=> %s::vector)) >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """
                    params.extend([str(query_vector), similarity_threshold, str(query_vector), limit])

                    cur.execute(query, params)
                    results = cur.fetchall()

                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error searching similar memories: {e}")
            return []

    def save_memory_embedding(
        self, agent_id: str, user_id: str, category: str, vector: List[float], content_text: str = None
    ) -> bool:
        """
        Save memory embedding vector for unified table.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Category (e.g., 'activity', 'profile', 'event', 'reminder', etc.)
            vector: Embedding vector
            content_text: Optional content text to update

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Get memory_id first
                    cur.execute(
                        "SELECT id FROM memories WHERE agent_id = %s AND user_id = %s AND category = %s",
                        (agent_id, user_id, category)
                    )
                    result = cur.fetchone()
                    
                    if not result:
                        logger.warning(f"No memory found for embedding update: {agent_id}/{user_id}/{category}")
                        return False
                    
                    memory_id = result[0]
                    
                    if content_text:
                        cur.execute(
                            """
                            UPDATE memories 
                            SET embedding = %s::vector, content = %s, updated_at = %s
                            WHERE agent_id = %s AND user_id = %s AND category = %s
                        """,
                            (str(vector), content_text, datetime.now(), agent_id, user_id, category),
                        )
                        
                        # Log both content and embedding update
                        self._log_history_action(
                            cur, memory_id, agent_id, user_id, "UPDATE",
                            section="content", content=content_text
                        )
                        self._log_history_action(
                            cur, memory_id, agent_id, user_id, "EMBED",
                            section="embedding"
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE memories 
                            SET embedding = %s::vector, updated_at = %s
                            WHERE agent_id = %s AND user_id = %s AND category = %s
                        """,
                            (str(vector), datetime.now(), agent_id, user_id, category),
                        )
                        
                        # Log embedding update only
                        self._log_history_action(
                            cur, memory_id, agent_id, user_id, "EMBED",
                            section="embedding"
                        )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error saving memory embedding: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # First, get the memory details for history logging
                    cur.execute(
                        "SELECT agent_id, user_id, category, content, links FROM memories WHERE id = %s",
                        (memory_id,)
                    )
                    memory_data = cur.fetchone()
                    
                    if memory_data:
                        agent_id, user_id, category, content, links = memory_data
                        
                        # Log the DELETE action to history before deletion
                        self._log_history_action(
                            cur, memory_id, agent_id, user_id, "DELETE",
                            section="full", content=content, links=json.loads(links) if links else None
                        )
                    
                    # Delete the memory
                    cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    def delete_agent_memories(self, agent_id: str, user_id: str = "default", content_type: str = None) -> bool:
        """
        Delete memories for an agent-user combination.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            content_type: Optional content type filter

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    if content_type:
                        cur.execute(
                            "DELETE FROM memories WHERE agent_id = %s AND user_id = %s AND category = %s",
                            (agent_id, user_id, content_type)
                        )
                    else:
                        cur.execute(
                            "DELETE FROM memories WHERE agent_id = %s AND user_id = %s",
                            (agent_id, user_id)
                        )
                    
                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting agent memories: {e}")
            return False

    def clear_agent_memories(self, agent_id: str, user_id: str, category: str = None) -> bool:
        """
        Clear all memories for an agent.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            category: Optional specific category to clear

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    if category:
                        cur.execute(
                            "DELETE FROM memories WHERE agent_id = %s AND user_id = %s AND category = %s",
                            (agent_id, user_id, category)
                        )
                    else:
                        cur.execute(
                            "DELETE FROM memories WHERE agent_id = %s AND user_id = %s",
                            (agent_id, user_id)
                        )
                    
                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error clearing agent memories: {e}")
            return False

    def get_memory_stats(self, agent_id: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Get comprehensive memory statistics for an agent.

        Args:
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            Dict with memory statistics
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Get basic stats
                    cur.execute(
                        """
                        SELECT
                            category,
                            COUNT(*) as count,
                            MAX(updated_at) as last_updated
                        FROM memories
                        WHERE agent_id = %s AND user_id = %s
                        GROUP BY category
                        ORDER BY count DESC
                    """,
                        (agent_id, user_id),
                    )

                    stats = {}
                    total_memories = 0
                    
                    for row in cur.fetchall():
                        category_stats = dict(row)
                        stats[row["category"]] = category_stats
                        total_memories += row["count"]

                    return {
                        "agent_id": agent_id,
                        "user_id": user_id,
                        "total_memories": total_memories,
                        "categories": stats,
                    }

        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    def log_memory_action(self, memory_id: str, agent_id: str, user_id: str, action: str, 
                         section: str = None, content: str = None, links: dict = None) -> bool:
        """
        Log an action to the memory history table.

        Args:
            memory_id: ID of the memory that was acted upon
            agent_id: Agent identifier
            user_id: User identifier
            action: Action type (CREATE, UPDATE, DELETE, READ, SEARCH, EMBED)
            section: Section that was affected (content, links, category, etc.)
            content: Content involved in the action
            links: Links data involved in the action

        Returns:
            bool: Whether the log entry was successfully created
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    history_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO memory_history
                        (id, memory_id, agent_id, user_id, action, timestamp, section, content, links)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            history_id,
                            memory_id,
                            agent_id,
                            user_id,
                            action,
                            datetime.now(),
                            section,
                            content,
                            json.dumps(links) if links else None
                        )
                    )
                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Error logging memory action: {e}")
            return False

    def get_memory_history(self, memory_id: str = None, agent_id: str = None, user_id: str = None, 
                          action: str = None, limit: int = 100) -> List[Dict]:
        """
        Get memory history records with optional filtering.

        Args:
            memory_id: Filter by specific memory ID
            agent_id: Filter by agent ID
            user_id: Filter by user ID
            action: Filter by action type
            limit: Maximum number of records to return

        Returns:
            List of history records
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Build dynamic query
                    where_conditions = []
                    params = []

                    if memory_id:
                        where_conditions.append("memory_id = %s")
                        params.append(memory_id)
                    
                    if agent_id:
                        where_conditions.append("agent_id = %s")
                        params.append(agent_id)
                    
                    if user_id:
                        where_conditions.append("user_id = %s")
                        params.append(user_id)
                    
                    if action:
                        where_conditions.append("action = %s")
                        params.append(action)

                    params.append(limit)

                    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                    
                    query = f"""
                        SELECT id, memory_id, agent_id, user_id, action, timestamp, 
                               section, content, links
                        FROM memory_history
                        WHERE {where_clause}
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """

                    cur.execute(query, params)
                    results = cur.fetchall()
                    
                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting memory history: {e}")
            return []


# PostgreSQLConversationDB class removed - depends on deleted memo module
