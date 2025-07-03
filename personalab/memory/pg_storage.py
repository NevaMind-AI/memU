"""
PostgreSQL memory database storage layer module.

Implements PostgreSQL + pgvector storage for Memory objects:
- memories table: stores Memory basic information and metadata
- memory_contents table: unified storage for profile and event contents
- vector storage using pgvector extension for semantic search
- supports complete Memory CRUD operations
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector

from .base import EventMemory, Memory, ProfileMemory


class PostgreSQLMemoryDB:
    """
    PostgreSQL Memory database operations repository.

    Provides complete database storage and management functionality for Memory objects
    using PostgreSQL with pgvector extension for vector storage.
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
        """Initialize database table structure with pgvector support."""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

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

                conn.commit()

                # Register pgvector types
                register_vector(conn)

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
        Search for similar memory contents using pgvector cosine similarity.

        Args:
            agent_id: Agent ID
            query_vector: Query vector for similarity search
            content_type: Filter by content type (optional)
            limit: Maximum results
            similarity_threshold: Minimum similarity score

        Returns:
            List[Dict]: Similar memory contents with similarity scores
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    register_vector(conn)

                    query = """
                        SELECT
                            mc.content_id,
                            mc.memory_id,
                            mc.content_type,
                            mc.content_text,
                            mc.content_data,
                            m.agent_id,
                            m.user_id,
                            1 - (mc.content_vector <=> %s) as similarity_score
                        FROM memory_contents mc
                        JOIN memories m ON mc.memory_id = m.memory_id
                        WHERE m.agent_id = %s
                        AND mc.content_vector IS NOT NULL
                    """

                    params = [query_vector, agent_id]

                    if content_type:
                        query += " AND mc.content_type = %s"
                        params.append(content_type)

                    query += """
                        AND (1 - (mc.content_vector <=> %s)) >= %s
                        ORDER BY mc.content_vector <=> %s
                        LIMIT %s
                    """
                    params.extend(
                        [query_vector, similarity_threshold, query_vector, limit]
                    )

                    cur.execute(query, params)
                    rows = cur.fetchall()

                    return [dict(row) for row in rows]

        except Exception as e:
            print(f"Error searching similar memories: {e}")
            return []

    def save_memory_embedding(
        self, memory_id: str, content_type: str, vector: List[float], content_text: str
    ) -> bool:
        """
        Save or update vector embedding for memory content.

        Args:
            memory_id: Memory ID
            content_type: Type of content ('profile', 'event', 'mind')
            vector: Vector embedding
            content_text: Original text content

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    register_vector(conn)

                    cur.execute(
                        """
                        UPDATE memory_contents
                        SET content_vector = %s, content_text = %s, updated_at = %s
                        WHERE memory_id = %s AND content_type = %s
                    """,
                        (vector, content_text, datetime.now(), memory_id, content_type),
                    )

                    conn.commit()
                    return True

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
        content_data = {
            "events": event_memory.get_content(),
            "max_events": event_memory.max_events,
        }

        content_id = f"{memory_id}_event"
        content_text = " ".join(event_memory.get_content())
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

    def _calculate_hash(self, content: str) -> str:
        """Calculate content hash."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def close(self):
        """Close database connection (PostgreSQL handles connection pooling)."""
        pass
