"""
Conversation database storage layer.

Handles database operations for conversation recording, retrieval, and vector storage.
"""

import json
import hashlib
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from .models import Conversation, ConversationMessage


class ConversationDB:
    """
    Conversation database operations.
    
    Provides database storage and management functionality for conversations,
    messages, and vector embeddings.
    """
    
    def __init__(self, db_path: str = "conversations.db"):
        """
        Initialize conversation database.
        
        Args:
            db_path: Database file path
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize conversation database table structure"""
        with sqlite3.connect(self.db_path) as conn:
            # Create conversations table (Conversation recording)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,           -- User identifier for conversation filtering (REQUIRED)
                    created_at TEXT NOT NULL,
                    conversation_data TEXT NOT NULL,  -- JSON array of messages
                    pipeline_result TEXT,            -- Pipeline execution results
                    memory_id TEXT,                  -- Associated memory ID
                    session_id TEXT,                 -- Session identifier
                    turn_count INTEGER DEFAULT 0,    -- Number of conversation turns
                    summary TEXT                     -- Conversation summary
                )
            """)
            
            # Create conversation_messages table (Individual messages)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    message_index INTEGER NOT NULL,  -- Order within conversation
                    created_at TEXT NOT NULL,
                    
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                    UNIQUE(conversation_id, message_index)
                )
            """)
            
            # Create embedding_vectors table (Vector storage for semantic search)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_vectors (
                    vector_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL CHECK (source_type IN ('conversation', 'message', 'memory')),
                    source_id TEXT NOT NULL,         -- conversation_id, message_id, or memory_id
                    agent_id TEXT NOT NULL,
                    vector_data TEXT NOT NULL,       -- JSON array of float values
                    vector_dimension INTEGER NOT NULL,
                    content_text TEXT NOT NULL,      -- Original text for the vector
                    content_hash TEXT NOT NULL,      -- Hash of content for deduplication
                    embedding_model TEXT,            -- Model used for embedding
                    created_at TEXT NOT NULL,
                    
                    UNIQUE(source_type, source_id)
                )
            """)
            
            # Create indexes separately
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)")
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON conversation_messages(role)")
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_agent_id ON embedding_vectors(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_source_type ON embedding_vectors(source_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_content_hash ON embedding_vectors(content_hash)")
            
            conn.commit()
    
    def save_conversation(self, conversation: Conversation) -> bool:
        """
        Save conversation to database.
        
        Args:
            conversation: Conversation object to save
            
        Returns:
            bool: Whether save was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Save conversation record
                conn.execute("""
                    INSERT OR REPLACE INTO conversations 
                    (conversation_id, agent_id, user_id, created_at, conversation_data, 
                     pipeline_result, memory_id, session_id, turn_count, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    conversation.conversation_id,
                    conversation.agent_id,
                    conversation.user_id,
                    conversation.created_at.isoformat(),
                    json.dumps([msg.to_dict() for msg in conversation.messages]),
                    json.dumps(conversation.pipeline_result) if conversation.pipeline_result else None,
                    conversation.memory_id,
                    conversation.session_id,
                    conversation.turn_count,
                    conversation.summary
                ])
                
                # Delete existing messages for this conversation
                conn.execute("""
                    DELETE FROM conversation_messages WHERE conversation_id = ?
                """, [conversation.conversation_id])
                
                # Save individual messages
                for message in conversation.messages:
                    conn.execute("""
                        INSERT INTO conversation_messages 
                        (message_id, conversation_id, role, content, message_index, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        message.message_id,
                        conversation.conversation_id,
                        message.role,
                        message.content,
                        message.message_index,
                        message.created_at.isoformat()
                    ])
                
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get conversation metadata
                conv_row = conn.execute("""
                    SELECT * FROM conversations WHERE conversation_id = ?
                """, [conversation_id]).fetchone()
                
                if not conv_row:
                    return None
                
                # Get messages
                message_rows = conn.execute("""
                    SELECT * FROM conversation_messages 
                    WHERE conversation_id = ? 
                    ORDER BY message_index
                """, [conversation_id]).fetchall()
                
                # Convert to ConversationMessage objects
                messages = []
                for msg_row in message_rows:
                    message = ConversationMessage(
                        role=msg_row["role"],
                        content=msg_row["content"],
                        message_index=msg_row["message_index"],
                        message_id=msg_row["message_id"],
                        created_at=datetime.fromisoformat(msg_row["created_at"])
                    )
                    messages.append(message)
                
                # Validate required fields from database
                if not conv_row["agent_id"]:
                    raise ValueError(f"Missing agent_id for conversation {conversation_id}")
                if not conv_row["user_id"]:
                    raise ValueError(f"Missing user_id for conversation {conversation_id}")
                if not conv_row["created_at"]:
                    raise ValueError(f"Missing created_at for conversation {conversation_id}")
                
                # Create Conversation object
                conversation = Conversation(
                    agent_id=conv_row["agent_id"],
                    user_id=conv_row["user_id"],
                    messages=[],  # Will be set below
                    session_id=conv_row["session_id"],
                    conversation_id=conv_row["conversation_id"],
                    created_at=datetime.fromisoformat(conv_row["created_at"]),
                    memory_id=conv_row["memory_id"],
                    pipeline_result=json.loads(conv_row["pipeline_result"]) if conv_row["pipeline_result"] else None
                )
                
                conversation.messages = messages
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
        user_id: Optional[str] = None
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                    SELECT conversation_id, agent_id, user_id, created_at, turn_count, summary, session_id, memory_id
                    FROM conversations 
                    WHERE agent_id = ?
                """
                params = [agent_id]
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                rows = conn.execute(query, params).fetchall()
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
            with sqlite3.connect(self.db_path) as conn:
                # Delete messages first (foreign key constraint)
                conn.execute("""
                    DELETE FROM conversation_messages WHERE conversation_id = ?
                """, [conversation_id])
                
                # Delete conversation
                conn.execute("""
                    DELETE FROM conversations WHERE conversation_id = ?
                """, [conversation_id])
                
                # Delete related embeddings
                conn.execute("""
                    DELETE FROM embedding_vectors 
                    WHERE source_type = 'conversation' AND source_id = ?
                """, [conversation_id])
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    # ========== Vector Embedding Methods ==========
    
    def save_embedding(
        self,
        source_type: str,
        source_id: str,
        agent_id: str,
        vector: List[float],
        content_text: str,
        embedding_model: str = "default"
    ) -> bool:
        """
        Save vector embedding to database.
        
        Args:
            source_type: Type of source ('conversation', 'message', 'memory')
            source_id: ID of the source
            agent_id: Agent ID
            vector: Vector embedding as list of floats
            content_text: Original text content
            embedding_model: Model used for embedding
            
        Returns:
            bool: Whether save was successful
        """
        vector_id = str(uuid.uuid4())
        content_hash = self._calculate_hash(content_text)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO embedding_vectors 
                    (vector_id, source_type, source_id, agent_id, vector_data, 
                     vector_dimension, content_text, content_hash, embedding_model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    vector_id,
                    source_type,
                    source_id,
                    agent_id,
                    json.dumps(vector),
                    len(vector),
                    content_text,
                    content_hash,
                    embedding_model,
                    datetime.now().isoformat()
                ])
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving embedding: {e}")
            return False
    
    def get_embeddings_by_agent(
        self, 
        agent_id: str, 
        source_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get embeddings for an agent.
        
        Args:
            agent_id: Agent ID
            source_type: Filter by source type (optional)
            limit: Maximum number of embeddings
            
        Returns:
            List[Dict]: List of embeddings
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                    SELECT vector_id, source_type, source_id, vector_data, 
                           content_text, embedding_model, created_at
                    FROM embedding_vectors 
                    WHERE agent_id = ?
                """
                params = [agent_id]
                
                if source_type:
                    query += " AND source_type = ?"
                    params.append(source_type)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            return []
    
    def search_similar_vectors(
        self,
        agent_id: str,
        query_vector: List[float],
        source_type: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            agent_id: Agent ID
            query_vector: Query vector for similarity search
            source_type: Filter by source type (optional)
            limit: Maximum results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List[Dict]: Similar vectors with similarity scores
        """
        try:
            embeddings = self.get_embeddings_by_agent(agent_id, source_type, limit * 3)
            
            results = []
            for embedding in embeddings:
                stored_vector = json.loads(embedding['vector_data'])
                similarity = self._cosine_similarity(query_vector, stored_vector)
                
                if similarity >= similarity_threshold:
                    results.append({
                        **embedding,
                        'similarity_score': similarity
                    })
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"Error searching similar vectors: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        try:
            import math
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate content hash"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def close(self):
        """Close database connection"""
        pass 