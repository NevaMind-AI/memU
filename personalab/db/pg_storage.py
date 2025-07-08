"""
PostgreSQL storage layer for PersonaLab.

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
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector

from ..memory.base import EventMemory, Memory, ProfileMemory
from ..memo.models import Conversation, ConversationMessage
from ..utils import get_logger
from .utils import build_connection_string, test_database_connection, ensure_pgvector_extension

logger = get_logger(__name__)


class PostgreSQLStorageBase:
    """
    Base class for PostgreSQL storage operations.
    
    Provides common functionality for database connection, initialization,
    and utility methods shared by Memory and Conversation storage.
    """

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

        self._test_connection()
        self._init_database()

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
            
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Create tables specific to this storage type
                    self._init_tables(cur)
                    conn.commit()
                    
                    # Register pgvector types
                    register_vector(conn)
                    
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
        """Initialize memory-specific database tables."""
        # Create main memories table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                version INTEGER DEFAULT 3,

                -- Embedded content for simplified access
                profile_content JSONB,
                event_content JSONB,
                mind_content JSONB,

                -- Memory statistics
                profile_content_hash TEXT,
                last_event_date TIMESTAMP,

                -- Unique constraint for agent-user combination
                UNIQUE(agent_id, user_id)
            )
        """
        )

        # Create memory_contents table with vector support
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_contents (
                content_id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                content_type TEXT NOT NULL CHECK (content_type IN ('profile', 'event', 'mind')),

                -- Content data
                content_data JSONB NOT NULL,
                content_text TEXT,
                content_hash TEXT,

                -- Vector embedding for semantic search
                content_vector vector(1536),  -- Default OpenAI embedding dimension

                -- Metadata
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,

                FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE,
                UNIQUE(memory_id, content_type)
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
            "CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_contents_memory_type ON memory_contents(memory_id, content_type)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_contents_hash ON memory_contents(content_hash)"
        )

        # Create vector similarity search index using HNSW
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_contents_vector_hnsw
            ON memory_contents USING hnsw (content_vector vector_cosine_ops)
        """
        )

    def save_memory(self, memory: Memory) -> bool:
        """
        Save complete Memory object to database.
        
        Design: 
        - memories table: metadata only (memory_id, agent_id, user_id, timestamps)
        - memory_contents table: all content (profile, events, mind) with vectors

        Args:
            memory: Memory object

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # 1. Save/update metadata in memories table (no content)
                    cur.execute(
                        """
                        INSERT INTO memories
                        (memory_id, agent_id, user_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (agent_id, user_id) DO UPDATE SET
                        memory_id = EXCLUDED.memory_id,
                        updated_at = EXCLUDED.updated_at
                        """,
                        (
                            memory.memory_id,
                            memory.agent_id,
                            memory.user_id,
                            memory.created_at,
                            memory.updated_at,
                        ),
                    )

                    # 2. Save content to memory_contents table
                    profile_content = memory.get_profile()
                    if profile_content:
                        self._save_content(cur, memory.memory_id, 'profile', profile_content)

                    event_content = memory.get_events()
                    if event_content:
                        self._save_content(cur, memory.memory_id, 'event', event_content)

                    mind_content = memory.get_mind()
                    if mind_content:
                        self._save_content(cur, memory.memory_id, 'mind', mind_content)

                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False

    def _save_content(self, cur, memory_id: str, content_type: str, content: list):
        """Save content to memory_contents table using consistent new format."""
        # Use consistent new format: {"profile": [...], "event": [...], "mind": [...]}
        content_data = {content_type: content}
        content_id = f"{memory_id}_{content_type}"
        content_text = "\n".join(content) if isinstance(content, list) else str(content)
        content_hash = self._calculate_hash(content_text)

        cur.execute(
            """
            INSERT INTO memory_contents
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (memory_id, content_type) DO UPDATE SET
            content_data = EXCLUDED.content_data,
            content_text = EXCLUDED.content_text,
            content_hash = EXCLUDED.content_hash,
            updated_at = EXCLUDED.updated_at
            """,
            (
                content_id,
                memory_id,
                content_type,
                json.dumps(content_data),
                content_text,
                content_hash,
                datetime.now(),
                datetime.now(),
            ),
        )

    def load_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Load complete Memory object from database.
        
        Design:
        - Load metadata from memories table
        - Load all content from memory_contents table

        Args:
            memory_id: Memory ID

        Returns:
            Optional[Memory]: Memory object, returns None if not exists
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # 1. Load metadata from memories table
                    cur.execute(
                        "SELECT * FROM memories WHERE memory_id = %s", (memory_id,)
                    )
                    memory_row = cur.fetchone()

                    if not memory_row:
                        return None

                    # 2. Create Memory object with metadata
                    memory = Memory(
                        agent_id=memory_row["agent_id"],
                        user_id=memory_row.get("user_id", "default_user"),
                        memory_client=None,  # No API client needed for database operations
                        memory_id=memory_id,
                    )
                    memory.created_at = memory_row["created_at"]
                    memory.updated_at = memory_row["updated_at"]

                    # 3. Load all content from memory_contents table
                    cur.execute(
                        """
                        SELECT content_type, content_data 
                        FROM memory_contents 
                        WHERE memory_id = %s
                        """, 
                        (memory_id,)
                    )
                    
                    content_rows = cur.fetchall()
                    for row in content_rows:
                        content_type = row["content_type"]
                        content_data = row["content_data"]
                        
                        try:
                            # Parse content_data JSON
                            if isinstance(content_data, str):
                                content_json = json.loads(content_data)
                            else:
                                content_json = content_data
                            
                            # Extract content using new unified format
                            if content_type == 'profile' and 'profile' in content_json:
                                memory.profile_memory = ProfileMemory(content_json['profile'])
                            elif content_type == 'event' and 'event' in content_json:
                                memory.event_memory = EventMemory(content_json['event'])
                            elif content_type == 'mind' and 'mind' in content_json:
                                memory.mind_content = content_json['mind']
                                
                        except (json.JSONDecodeError, TypeError, KeyError) as e:
                            logger.warning(f"Error parsing {content_type} content: {e}")

                    return memory

        except Exception as e:
            logger.error(f"Error loading memory: {e}")
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
                        "SELECT memory_id FROM memories WHERE agent_id = %s AND user_id = %s",
                        (agent_id, user_id),
                    )
                    result = cur.fetchone()

                    if not result:
                        return None

                    # Load complete memory using memory_id
                    return self.load_memory(result["memory_id"])

        except Exception as e:
            logger.error(f"Error getting memory by agent: {e}")
            return None

    def search_similar_memories(
        self,
        agent_id: str,
        query_vector: List[float],
        content_type: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using vector similarity.

        Args:
            agent_id: Agent ID
            query_vector: Query vector for similarity search
            content_type: Content type filter ('profile', 'event', 'mind')
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
                            mc.memory_id,
                            mc.content_type,
                            mc.content_data,
                            mc.content_text,
                            m.agent_id,
                            m.user_id,
                            m.updated_at,
                            1 - (mc.content_vector <=> %s::vector) as similarity
                        FROM memory_contents mc
                        JOIN memories m ON mc.memory_id = m.memory_id
                        WHERE m.agent_id = %s
                        AND mc.content_vector IS NOT NULL
                    """

                    params = [str(query_vector), agent_id]

                    # Add content type filter if specified
                    if content_type:
                        query += " AND mc.content_type = %s"
                        params.append(content_type)

                    # Add similarity threshold and ordering
                    query += """
                        AND (1 - (mc.content_vector <=> %s::vector)) >= %s
                        ORDER BY mc.content_vector <=> %s::vector
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
        self, memory_id: str, content_type: str, vector: List[float], content_text: str
    ) -> bool:
        """
        Save memory content embedding vector.

        Args:
            memory_id: Memory ID
            content_type: Content type ('profile', 'event', 'mind')
            vector: Embedding vector
            content_text: Content text for the vector

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE memory_contents 
                        SET content_vector = %s::vector, content_text = %s, updated_at = %s
                        WHERE memory_id = %s AND content_type = %s
                    """,
                        (str(vector), content_text, datetime.now(), memory_id, content_type),
                    )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error saving memory embedding: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete Memory and all its content from database.

        Args:
            memory_id: Memory ID

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Delete from memories table (cascade will handle related records)
                    cur.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))

                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get Memory statistics.

        Args:
            agent_id: Agent ID

        Returns:
            Dict: Statistics information
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) as total_memories,
                            MAX(updated_at) as last_updated
                        FROM memories
                        WHERE agent_id = %s
                    """,
                        (agent_id,),
                    )

                    stats_row = cur.fetchone()

                    return {
                        "agent_id": agent_id,
                        "total_memories": stats_row["total_memories"],
                        "last_updated": (
                            stats_row["last_updated"].isoformat()
                            if stats_row["last_updated"]
                            else None
                        ),
                    }

        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}


class PostgreSQLConversationDB(PostgreSQLStorageBase):
    """
    PostgreSQL Conversation database operations.

    Provides database storage and management functionality for conversations,
    messages, and vector embeddings using PostgreSQL with pgvector.
    """

    def _init_tables(self, cur):
        """Initialize conversation-specific database tables."""
        # Create conversations table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                conversation_data JSONB NOT NULL,
                pipeline_result JSONB,
                memory_id TEXT,
                session_id TEXT,
                conversation_vector vector(1536)  -- For conversation-level embeddings
            )
        """
        )

        # Create indexes for better performance
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)"
        )

        # Create vector similarity search index using HNSW
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_vector_hnsw
            ON conversations USING hnsw (conversation_vector vector_cosine_ops)
        """
        )

    def save_conversation(self, conversation: Conversation) -> bool:
        """
        Save conversation to PostgreSQL database.

        Args:
            conversation: Conversation object to save

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Save conversation record
                    cur.execute(
                        """
                        INSERT INTO conversations
                        (conversation_id, agent_id, user_id, created_at, conversation_data,
                         pipeline_result, memory_id, session_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (conversation_id) DO UPDATE SET
                        conversation_data = EXCLUDED.conversation_data,
                        pipeline_result = EXCLUDED.pipeline_result,
                        memory_id = EXCLUDED.memory_id,
                        session_id = EXCLUDED.session_id
                    """,
                        [
                            conversation.conversation_id,
                            conversation.agent_id,
                            conversation.user_id,
                            conversation.created_at,
                            json.dumps(
                                [msg.to_dict() for msg in conversation.messages]
                            ),
                            (
                                json.dumps(conversation.pipeline_result)
                                if conversation.pipeline_result
                                else None
                            ),
                            conversation.memory_id,
                            conversation.session_id,
                        ],
                    )

                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Optional[Conversation]: Conversation object or None
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Get conversation record
                    cur.execute(
                        "SELECT * FROM conversations WHERE conversation_id = %s",
                        [conversation_id],
                    )

                    conv_row = cur.fetchone()
                    if not conv_row:
                        return None

                    # Parse messages from conversation_data JSONB
                    messages = []
                    if conv_row["conversation_data"]:
                        try:
                            # conversation_data contains the list of message dictionaries
                            message_data_list = conv_row["conversation_data"]
                            if isinstance(message_data_list, str):
                                message_data_list = json.loads(message_data_list)
                            
                            for msg_data in message_data_list:
                                message = ConversationMessage(
                                    role=msg_data["role"],
                                    content=msg_data["content"],
                                    message_index=msg_data.get("message_index", 0),
                                    message_id=msg_data.get("message_id", ""),
                                    created_at=msg_data.get("created_at"),
                                )
                                messages.append(message)
                        except (json.JSONDecodeError, TypeError, KeyError) as e:
                            logger.warning(f"Error parsing conversation data: {e}")

                    # Create Conversation object
                    conversation = Conversation(
                        messages=messages,
                        agent_id=conv_row["agent_id"],
                        user_id=conv_row["user_id"],
                        conversation_id=conv_row["conversation_id"],
                        created_at=conv_row["created_at"],
                    )

                    if conv_row["pipeline_result"]:
                        conversation.pipeline_result = conv_row["pipeline_result"]
                    if conv_row["memory_id"]:
                        conversation.memory_id = conv_row["memory_id"]
                    if conv_row["session_id"]:
                        conversation.session_id = conv_row["session_id"]

                    return conversation

        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None

    def get_conversations_by_agent(
        self,
        agent_id: str,
        limit: int = 20,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversations by agent.

        Args:
            agent_id: Agent ID
            limit: Maximum number of conversations
            session_id: Optional session ID filter
            user_id: Optional user ID filter

        Returns:
            List[Dict]: List of conversation metadata
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Build query with filters
                    query = """
                        SELECT conversation_id, agent_id, user_id, created_at, 
                               memory_id, session_id
                        FROM conversations 
                        WHERE agent_id = %s
                    """
                    params = [agent_id]

                    if session_id:
                        query += " AND session_id = %s"
                        params.append(session_id)

                    if user_id:
                        query += " AND user_id = %s"
                        params.append(user_id)

                    query += " ORDER BY created_at DESC LIMIT %s"
                    params.append(limit)

                    cur.execute(query, params)
                    results = cur.fetchall()

                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting conversations by agent: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation and all related messages.

        Args:
            conversation_id: Conversation ID

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Delete conversation (CASCADE will handle messages)
                    cur.execute(
                        "DELETE FROM conversations WHERE conversation_id = %s",
                        [conversation_id],
                    )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False

    def save_conversation_embedding(
        self, conversation_id: str, vector: List[float], content_text: str
    ) -> bool:
        """
        Save conversation-level embedding.

        Args:
            conversation_id: Conversation ID
            vector: Embedding vector
            content_text: Content text for the vector

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE conversations 
                        SET conversation_vector = %s::vector
                        WHERE conversation_id = %s
                    """,
                        [str(vector), conversation_id],
                    )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Error saving conversation embedding: {e}")
            return False

    def search_similar_conversations(
        self,
        agent_id: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar conversations using vector similarity.

        Args:
            agent_id: Agent ID
            query_vector: Query vector for similarity search
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List[Dict]: List of similar conversations with metadata
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT 
                            conversation_id,
                            agent_id,
                            user_id,
                            created_at,
                            memory_id,
                            session_id,
                            1 - (conversation_vector <=> %s::vector) as similarity
                        FROM conversations
                        WHERE agent_id = %s
                        AND conversation_vector IS NOT NULL
                        AND (1 - (conversation_vector <=> %s::vector)) >= %s
                        ORDER BY conversation_vector <=> %s::vector
                        LIMIT %s
                    """,
                        [
                            str(query_vector),
                            agent_id,
                            str(query_vector),
                            similarity_threshold,
                            str(query_vector),
                            limit,
                        ],
                    )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error searching similar conversations: {e}")
            return [] 