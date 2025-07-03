"""
PostgreSQL conversation database storage layer.

Implements PostgreSQL + pgvector storage for conversations and messages:
- conversations table: stores conversation metadata
- conversation_messages table: stores individual messages
- vector storage using pgvector extension for semantic search
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

from .models import Conversation, ConversationMessage


class PostgreSQLConversationDB:
    """
    PostgreSQL Conversation database operations.

    Provides database storage and management functionality for conversations,
    messages, and vector embeddings using PostgreSQL with pgvector.
    """

    def __init__(self, connection_string: Optional[str] = None, **kwargs):
        """
        Initialize PostgreSQL conversation database.

        Args:
            connection_string: PostgreSQL connection string
            **kwargs: Connection parameters (host, port, dbname, user, password)
        """
        if connection_string:
            self.connection_string = connection_string
        else:
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
        """Initialize conversation database table structure with pgvector."""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

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

                conn.commit()

                # Register pgvector types
                register_vector(conn)

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
            Conversation: Conversation object or None
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Get conversation metadata
                    cur.execute(
                        "SELECT * FROM conversations WHERE conversation_id = %s",
                        (conversation_id,),
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
                        (conversation_id,),
                    )
                    message_rows = cur.fetchall()

                    # Convert to ConversationMessage objects
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

                    # Validate required fields
                    if not conv_row["agent_id"]:
                        raise ValueError(
                            f"Missing agent_id for conversation {conversation_id}"
                        )
                    if not conv_row["user_id"]:
                        raise ValueError(
                            f"Missing user_id for conversation {conversation_id}"
                        )

                    # Create Conversation object
                    conversation = Conversation(
                        agent_id=conv_row["agent_id"],
                        user_id=conv_row["user_id"],
                        messages=[msg.to_dict() for msg in messages],
                        session_id=conv_row["session_id"],
                        memory_id=conv_row["memory_id"],
                        pipeline_result=conv_row["pipeline_result"],
                        conversation_id=conv_row["conversation_id"],
                        created_at=conv_row["created_at"],
                    )

                    # Set additional attributes
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
        Get conversations for an agent.

        Args:
            agent_id: Agent ID
            limit: Maximum number of conversations
            session_id: Filter by session ID (optional)
            user_id: Filter by user ID (optional)

        Returns:
            List[Dict]: List of conversation summaries
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    query = """
                        SELECT conversation_id, agent_id, user_id, created_at, turn_count, summary, session_id, memory_id
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
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]

        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation and its messages.

        Args:
            conversation_id: Conversation ID

        Returns:
            bool: Whether deletion was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Delete conversation (CASCADE will handle messages and embeddings)
                    cur.execute(
                        "DELETE FROM conversations WHERE conversation_id = %s",
                        (conversation_id,),
                    )

                    conn.commit()
                    return True

        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False

    # ========== Vector Embedding Methods ==========

    def save_conversation_embedding(
        self, conversation_id: str, vector: List[float], content_text: str
    ) -> bool:
        """
        Save conversation-level embedding directly in conversations table.

        Args:
            conversation_id: Conversation ID
            vector: Vector embedding
            content_text: Original conversation text

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    register_vector(conn)

                    cur.execute(
                        """
                        UPDATE conversations
                        SET conversation_vector = %s
                        WHERE conversation_id = %s
                    """,
                        (vector, conversation_id),
                    )

                    conn.commit()
                    return True

        except Exception as e:
            print(f"Error saving conversation embedding: {e}")
            return False

    def save_message_embedding(self, message_id: str, vector: List[float]) -> bool:
        """
        Save message-level embedding directly in conversation_messages table.

        Args:
            message_id: Message ID
            vector: Vector embedding

        Returns:
            bool: Whether save was successful
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    register_vector(conn)

                    cur.execute(
                        """
                        UPDATE conversation_messages
                        SET message_vector = %s
                        WHERE message_id = %s
                    """,
                        (vector, message_id),
                    )

                    conn.commit()
                    return True

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
        Search for similar conversations using pgvector cosine similarity.

        Args:
            agent_id: Agent ID
            query_vector: Query vector for similarity search
            limit: Maximum results
            similarity_threshold: Minimum similarity score

        Returns:
            List[Dict]: Similar conversations with similarity scores
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    register_vector(conn)

                    # Convert query_vector to the proper format for pgvector
                    vector_param = f"[{','.join(map(str, query_vector))}]"

                    cur.execute(
                        """
                        SELECT
                            conversation_id,
                            agent_id,
                            user_id,
                            created_at,
                            summary,
                            session_id,
                            turn_count,
                            1 - (conversation_vector <=> %s::vector) as similarity_score
                        FROM conversations
                        WHERE agent_id = %s
                        AND conversation_vector IS NOT NULL
                        AND (1 - (conversation_vector <=> %s::vector)) >= %s
                        ORDER BY conversation_vector <=> %s::vector
                        LIMIT %s
                    """,
                        (
                            vector_param,
                            agent_id,
                            vector_param,
                            similarity_threshold,
                            vector_param,
                            limit,
                        ),
                    )

                    rows = cur.fetchall()
                    return [dict(row) for row in rows]

        except Exception as e:
            print(f"Error searching similar conversations: {e}")
            return []

    def _calculate_hash(self, content: str) -> str:
        """Calculate content hash."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def close(self):
        """Close database connection (PostgreSQL handles connection pooling)."""
        pass
