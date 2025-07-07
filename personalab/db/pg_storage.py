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
            self.connection_string = self._build_connection_string(**kwargs)

        self._test_connection()
        self._init_database()

    def _build_connection_string(self, **kwargs) -> str:
        """Build connection string from parameters or environment variables."""
        params = {
            "host": kwargs.get("host", os.getenv("POSTGRES_HOST", "localhost")),
            "port": kwargs.get("port", os.getenv("POSTGRES_PORT", "5432")),
            "dbname": kwargs.get("dbname", os.getenv("POSTGRES_DB", "personalab")),
            "user": kwargs.get("user", os.getenv("POSTGRES_USER", "postgres")),
            "password": kwargs.get(
                "password", os.getenv("POSTGRES_PASSWORD", "postgres")
            ),
        }

        return f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['dbname']}"

    def _test_connection(self):
        """Test database connection."""
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def _init_database(self):
        """Initialize database with pgvector extension and create tables."""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
                # Create tables specific to this storage type
                self._init_tables(cur)
                
                conn.commit()
                
                # Register pgvector types
                register_vector(conn)

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
                profile_content TEXT,
                event_content JSONB,
                mind_content JSONB,

                -- Theory of Mind analysis results
                mind_metadata JSONB,
                confidence_score REAL DEFAULT 0.0,

                -- Memory statistics
                profile_content_hash TEXT,
                event_count INTEGER DEFAULT 0,
                last_event_date TIMESTAMP,

                -- Schema versioning for migrations
                schema_version INTEGER DEFAULT 3,

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
            "CREATE INDEX IF NOT EXISTS idx_memories_schema_version ON memories(schema_version)"
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

        Args:
            memory: Memory object

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # 1. Save Memory basic information
                    cur.execute(
                        """
                        INSERT INTO memories
                        (memory_id, agent_id, user_id, created_at, updated_at, mind_metadata,
                         profile_content_hash, event_count, last_event_date, profile_content,
                         event_content, mind_content)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (memory_id) DO UPDATE SET
                        updated_at = EXCLUDED.updated_at,
                        mind_metadata = EXCLUDED.mind_metadata,
                        profile_content_hash = EXCLUDED.profile_content_hash,
                        event_count = EXCLUDED.event_count,
                        last_event_date = EXCLUDED.last_event_date,
                        profile_content = EXCLUDED.profile_content,
                        event_content = EXCLUDED.event_content,
                        mind_content = EXCLUDED.mind_content
                    """,
                        (
                            memory.memory_id,
                            memory.agent_id,
                            memory.user_id,
                            memory.created_at,
                            memory.updated_at,
                            (
                                json.dumps(memory.mind_metadata)
                                if memory.mind_metadata
                                else None
                            ),
                            self._calculate_hash(memory.get_profile_content()),
                            len(memory.get_event_content()),
                            datetime.now(),
                            memory.get_profile_content(),
                            json.dumps(memory.get_event_content()),
                            json.dumps(memory.get_mind_content()),
                        ),
                    )

                    # 2. Save ProfileMemory content
                    if memory.get_profile_content():
                        self._save_profile_content(
                            cur, memory.memory_id, memory.profile_memory
                        )

                    # 3. Save EventMemory content
                    if memory.get_event_content():
                        self._save_event_content(
                            cur, memory.memory_id, memory.event_memory
                        )

                    conn.commit()
                    return True

        except Exception as e:
            print(f"Error saving memory: {e}")
            return False

    def load_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Load complete Memory object from database.

        Args:
            memory_id: Memory ID

        Returns:
            Optional[Memory]: Memory object, returns None if not exists
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # 1. Load Memory basic information
                    cur.execute(
                        "SELECT * FROM memories WHERE memory_id = %s", (memory_id,)
                    )
                    memory_row = cur.fetchone()

                    if not memory_row:
                        return None

                    # 2. Create Memory object
                    memory = Memory(
                        agent_id=memory_row["agent_id"],
                        user_id=memory_row.get("user_id", "default_user"),
                        memory_id=memory_id,
                    )
                    memory.created_at = memory_row["created_at"]
                    memory.updated_at = memory_row["updated_at"]

                    if memory_row["mind_metadata"]:
                        memory.mind_metadata = memory_row["mind_metadata"]

                    # 3. Load ProfileMemory content
                    profile_content = self._load_profile_content(cur, memory_id)
                    if profile_content:
                        memory.profile_memory = ProfileMemory(profile_content)

                    # 4. Load EventMemory content
                    event_content = self._load_event_content(cur, memory_id)
                    if event_content:
                        memory.event_memory = EventMemory(event_content)

                    return memory

        except Exception as e:
            print(f"Error loading memory: {e}")
            return None

    def get_memory_by_agent_and_user(
        self, agent_id: str, user_id: str
    ) -> Optional[Memory]:
        """
        Load Memory by Agent ID and User ID.

        Args:
            agent_id: Agent ID
            user_id: User ID

        Returns:
            Optional[Memory]: Memory object, returns None if not exists
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT memory_id FROM memories
                        WHERE agent_id = %s AND user_id = %s
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """,
                        (agent_id, user_id),
                    )

                    row = cur.fetchone()
                    if row:
                        return self.load_memory(row[0])

                    return None

        except Exception as e:
            print(f"Error loading memory by agent and user: {e}")
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
            print(f"Error searching similar memories: {e}")
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
            print(f"Error saving memory embedding: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete Memory object with CASCADE handling.

        Args:
            memory_id: Memory ID

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Delete main memory record (CASCADE will handle related content)
                    cur.execute(
                        "DELETE FROM memories WHERE memory_id = %s", (memory_id,)
                    )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            print(f"Error deleting memory: {e}")
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
                            MAX(updated_at) as last_updated,
                            SUM(event_count) as total_events
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
                        "total_events": stats_row["total_events"] or 0,
                    }

        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {}

    def _save_profile_content(self, cur, memory_id: str, profile_memory: ProfileMemory):
        """Save profile memory content."""
        content_data = {"paragraph": profile_memory.get_content()}

        content_id = f"{memory_id}_profile"
        content_text = profile_memory.get_content()
        content_hash = self._calculate_hash(content_text)

        cur.execute(
            """
            INSERT INTO memory_contents
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (%s, %s, 'profile', %s, %s, %s, %s, %s)
            ON CONFLICT (memory_id, content_type) DO UPDATE SET
            content_data = EXCLUDED.content_data,
            content_text = EXCLUDED.content_text,
            content_hash = EXCLUDED.content_hash,
            updated_at = EXCLUDED.updated_at
        """,
            (
                content_id,
                memory_id,
                json.dumps(content_data),
                content_text,
                content_hash,
                datetime.now(),
                datetime.now(),
            ),
        )

    def _save_event_content(self, cur, memory_id: str, event_memory: EventMemory):
        """Save event memory content."""
        events = event_memory.get_content()
        content_data = {"events": events}

        content_id = f"{memory_id}_event"
        content_text = "\n".join(events)  # Combine events for text search
        content_hash = self._calculate_hash(content_text)

        cur.execute(
            """
            INSERT INTO memory_contents
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (%s, %s, 'event', %s, %s, %s, %s, %s)
            ON CONFLICT (memory_id, content_type) DO UPDATE SET
            content_data = EXCLUDED.content_data,
            content_text = EXCLUDED.content_text,
            content_hash = EXCLUDED.content_hash,
            updated_at = EXCLUDED.updated_at
        """,
            (
                content_id,
                memory_id,
                json.dumps(content_data),
                content_text,
                content_hash,
                datetime.now(),
                datetime.now(),
            ),
        )

    def _load_profile_content(self, cur, memory_id: str) -> Optional[str]:
        """Load profile memory content."""
        cur.execute(
            """
            SELECT content_data FROM memory_contents
            WHERE memory_id = %s AND content_type = 'profile'
        """,
            (memory_id,),
        )

        row = cur.fetchone()
        if row:
            content_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            return content_data.get("paragraph", "")

        return None

    def _load_event_content(self, cur, memory_id: str) -> Optional[List[str]]:
        """Load event memory content."""
        cur.execute(
            """
            SELECT content_data FROM memory_contents
            WHERE memory_id = %s AND content_type = 'event'
        """,
            (memory_id,),
        )

        row = cur.fetchone()
        if row:
            content_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            return content_data.get("events", [])

        return None


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
                turn_count INTEGER DEFAULT 0,
                summary TEXT,
                conversation_vector vector(1536)  -- For conversation-level embeddings
            )
        """
        )

        # Create conversation_messages table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                message_index INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                message_vector vector(1536),  -- For message-level embeddings

                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                UNIQUE(conversation_id, message_index)
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

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_role ON conversation_messages(role)"
        )

        # Create vector similarity search indexes using HNSW
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_vector_hnsw
            ON conversations USING hnsw (conversation_vector vector_cosine_ops)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_vector_hnsw
            ON conversation_messages USING hnsw (message_vector vector_cosine_ops)
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
                         pipeline_result, memory_id, session_id, turn_count, summary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (conversation_id) DO UPDATE SET
                        conversation_data = EXCLUDED.conversation_data,
                        pipeline_result = EXCLUDED.pipeline_result,
                        memory_id = EXCLUDED.memory_id,
                        session_id = EXCLUDED.session_id,
                        turn_count = EXCLUDED.turn_count,
                        summary = EXCLUDED.summary
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
                            conversation.turn_count,
                            conversation.summary,
                        ],
                    )

                    # Delete existing messages for this conversation
                    cur.execute(
                        "DELETE FROM conversation_messages WHERE conversation_id = %s",
                        [conversation.conversation_id],
                    )

                    # Save individual messages
                    for message in conversation.messages:
                        cur.execute(
                            """
                            INSERT INTO conversation_messages
                            (message_id, conversation_id, role, content, message_index, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                            [
                                message.message_id,
                                conversation.conversation_id,
                                message.role,
                                message.content,
                                message.message_index,
                                message.created_at,
                            ],
                        )

                    conn.commit()
                    return True

        except Exception as e:
            print(f"Error saving conversation: {e}")
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

                    # Get messages
                    cur.execute(
                        """
                        SELECT * FROM conversation_messages 
                        WHERE conversation_id = %s 
                        ORDER BY message_index
                    """,
                        [conversation_id],
                    )

                    message_rows = cur.fetchall()

                    # Create ConversationMessage objects
                    messages = []
                    for msg_row in message_rows:
                        message = ConversationMessage(
                            role=msg_row["role"],
                            content=msg_row["content"],
                            message_index=msg_row["message_index"],
                            message_id=msg_row["message_id"],
                            created_at=msg_row["created_at"],
                        )
                        messages.append(message)

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
                    if conv_row["turn_count"]:
                        conversation.turn_count = conv_row["turn_count"]
                    if conv_row["summary"]:
                        conversation.summary = conv_row["summary"]

                    return conversation

        except Exception as e:
            print(f"Error getting conversation: {e}")
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
                               memory_id, session_id, turn_count, summary
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
            print(f"Error getting conversations by agent: {e}")
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
            print(f"Error deleting conversation: {e}")
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
                        SET conversation_vector = %s::vector, summary = %s
                        WHERE conversation_id = %s
                    """,
                        [str(vector), content_text, conversation_id],
                    )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            print(f"Error saving conversation embedding: {e}")
            return False

    def save_message_embedding(self, message_id: str, vector: List[float]) -> bool:
        """
        Save message-level embedding.

        Args:
            message_id: Message ID
            vector: Embedding vector

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE conversation_messages 
                        SET message_vector = %s::vector
                        WHERE message_id = %s
                    """,
                        [str(vector), message_id],
                    )

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            print(f"Error saving message embedding: {e}")
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
                            turn_count,
                            summary,
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
            print(f"Error searching similar conversations: {e}")
            return [] 