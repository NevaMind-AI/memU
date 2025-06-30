"""
Memory database storage layer module.

Based on STRUCTURE.md design, implements database storage and management for Memory objects:
- memories table: stores Memory basic information and metadata
- memory_contents table: unified storage for profile and event contents
- conversations table: stores conversation history with vectorization
- embedding_vectors table: stores conversation embeddings for semantic search
- supports complete Memory CRUD operations
"""

import json
import hashlib
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from .base import Memory, ProfileMemory, EventMemory


class MemoryDB:
    """
    Memory database operations repository.
    
    Provides complete database storage and management functionality for Memory objects,
    conversation recording, and vector embeddings for semantic search.
    """
    
    def __init__(self, db_path: str = "memory.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Database file path
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database table structure"""
        with sqlite3.connect(self.db_path) as conn:
            # Create memories table (unified Memory table)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    
                    -- Theory of Mind analysis results
                    tom_metadata TEXT,
                    confidence_score REAL,
                    
                    -- Memory statistics
                    profile_content_hash TEXT,
                    event_count INTEGER DEFAULT 0,
                    last_event_date TEXT,
                    
                    -- Index
                    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
                )
            """)
            
            # Create memory_contents table (Memory content table)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_contents (
                    content_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    content_type TEXT NOT NULL CHECK (content_type IN ('profile', 'event')),
                    
                    -- Content data
                    content_data TEXT NOT NULL,
                    content_text TEXT,
                    content_hash TEXT,
                    
                    -- Metadata
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    
                    FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
                    UNIQUE(memory_id, content_type)
                )
            """)
            
            # Create conversations table (Conversation recording)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    conversation_data TEXT NOT NULL,  -- JSON array of messages
                    pipeline_result TEXT,            -- Pipeline execution results
                    memory_id TEXT,                  -- Associated memory ID
                    session_id TEXT,                 -- Session identifier
                    turn_count INTEGER DEFAULT 0,    -- Number of conversation turns
                    summary TEXT,                    -- Conversation summary
                    
                    FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
                    INDEX idx_agent_id (agent_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_session_id (session_id)
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
                    INDEX idx_conversation_id (conversation_id),
                    INDEX idx_role (role),
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
                    
                    FOREIGN KEY (agent_id) REFERENCES memories(agent_id),
                    INDEX idx_agent_id (agent_id),
                    INDEX idx_source_type (source_type),
                    INDEX idx_content_hash (content_hash),
                    UNIQUE(source_type, source_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_contents_memory_type ON memory_contents(memory_id, content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_contents_hash ON memory_contents(content_hash)")
            
            conn.commit()
    
    def save_memory(self, memory: Memory) -> bool:
        """
        Save complete Memory object to database.
        
        Args:
            memory: Memory object
            
        Returns:
            bool: Whether save was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 1. Save Memory basic information
                memory_data = {
                    'memory_id': memory.memory_id,
                    'agent_id': memory.agent_id,
                    'created_at': memory.created_at.isoformat(),
                    'updated_at': memory.updated_at.isoformat(),
                    'tom_metadata': json.dumps(memory.tom_metadata) if memory.tom_metadata else None,
                    'profile_content_hash': self._calculate_hash(memory.get_profile_content()),
                    'event_count': len(memory.get_event_content()),
                    'last_event_date': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO memories 
                    (memory_id, agent_id, created_at, updated_at, tom_metadata, 
                     profile_content_hash, event_count, last_event_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_data['memory_id'],
                    memory_data['agent_id'],
                    memory_data['created_at'],
                    memory_data['updated_at'],
                    memory_data['tom_metadata'],
                    memory_data['profile_content_hash'],
                    memory_data['event_count'],
                    memory_data['last_event_date']
                ))
                
                # 2. Save ProfileMemory content
                if memory.get_profile_content():
                    self._save_profile_content(conn, memory.memory_id, memory.profile_memory)
                
                # 3. Save EventMemory content
                if memory.get_event_content():
                    self._save_event_content(conn, memory.memory_id, memory.event_memory)
                
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 1. Load Memory basic information
                memory_row = conn.execute("""
                    SELECT * FROM memories WHERE memory_id = ?
                """, [memory_id]).fetchone()
                
                if not memory_row:
                    return None
                
                # 2. Create Memory object
                memory = Memory(
                    agent_id=memory_row['agent_id'],
                    memory_id=memory_id
                )
                memory.created_at = datetime.fromisoformat(memory_row['created_at'])
                memory.updated_at = datetime.fromisoformat(memory_row['updated_at'])
                
                if memory_row['tom_metadata']:
                    memory.tom_metadata = json.loads(memory_row['tom_metadata'])
                
                # 3. Load ProfileMemory content
                profile_content = self._load_profile_content(conn, memory_id)
                if profile_content:
                    memory.profile_memory = ProfileMemory(profile_content)
                
                # 4. Load EventMemory content
                event_content = self._load_event_content(conn, memory_id)
                if event_content:
                    memory.event_memory = EventMemory(event_content)
                
                return memory
                
        except Exception as e:
            print(f"Error loading memory: {e}")
            return None
    
    def get_memory_by_agent(self, agent_id: str) -> Optional[Memory]:
        """
        Load Memory by Agent ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Memory]: Memory object, returns None if not exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Find the latest Memory for this Agent
                memory_row = conn.execute("""
                    SELECT memory_id FROM memories 
                    WHERE agent_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT 1
                """, [agent_id]).fetchone()
                
                if memory_row:
                    return self.load_memory(memory_row['memory_id'])
                
                return None
                
        except Exception as e:
            print(f"Error loading memory by agent: {e}")
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete Memory object.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            bool: Whether deletion was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete memory_contents
                conn.execute("DELETE FROM memory_contents WHERE memory_id = ?", [memory_id])
                
                # Delete memories
                conn.execute("DELETE FROM memories WHERE memory_id = ?", [memory_id])
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def list_memories_by_agent(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List Memory records for specified Agent.
        
        Args:
            agent_id: Agent ID
            limit: Return count limit
            
        Returns:
            List[Dict]: Memory information list
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                rows = conn.execute("""
                    SELECT memory_id, created_at, updated_at, event_count, confidence_score
                    FROM memories 
                    WHERE agent_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, [agent_id, limit]).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []
    
    def _save_profile_content(self, conn: sqlite3.Connection, memory_id: str, profile_memory: ProfileMemory):
        """Save profile memory content"""
        content_data = {
            "paragraph": profile_memory.get_content()
        }
        
        content_id = f"{memory_id}_profile"
        content_text = profile_memory.get_content()
        content_hash = self._calculate_hash(content_text)
        
        conn.execute("""
            INSERT OR REPLACE INTO memory_contents 
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (?, ?, 'profile', ?, ?, ?, ?, ?)
        """, [
            content_id,
            memory_id,
            json.dumps(content_data),
            content_text,
            content_hash,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ])
    
    def _save_event_content(self, conn: sqlite3.Connection, memory_id: str, event_memory: EventMemory):
        """Save event memory content"""
        content_data = {
            "events": event_memory.get_content(),
            "max_events": event_memory.max_events
        }
        
        content_id = f"{memory_id}_event"
        content_text = ' '.join(event_memory.get_content())
        content_hash = self._calculate_hash(content_text)
        
        conn.execute("""
            INSERT OR REPLACE INTO memory_contents 
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (?, ?, 'event', ?, ?, ?, ?, ?)
        """, [
            content_id,
            memory_id,
            json.dumps(content_data),
            content_text,
            content_hash,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ])
    
    def _load_profile_content(self, conn: sqlite3.Connection, memory_id: str) -> Optional[str]:
        """Load profile memory content"""
        row = conn.execute("""
            SELECT content_data FROM memory_contents 
            WHERE memory_id = ? AND content_type = 'profile'
        """, [memory_id]).fetchone()
        
        if row:
            content_data = json.loads(row[0])
            return content_data.get('paragraph', '')
        
        return None
    
    def _load_event_content(self, conn: sqlite3.Connection, memory_id: str) -> Optional[List[str]]:
        """Load event memory content"""
        row = conn.execute("""
            SELECT content_data FROM memory_contents 
            WHERE memory_id = ? AND content_type = 'event'
        """, [memory_id]).fetchone()
        
        if row:
            content_data = json.loads(row[0])
            return content_data.get('events', [])
        
        return None
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate content hash"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get Memory statistics.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: Statistics information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Basic statistics
                stats_row = conn.execute("""
                    SELECT 
                        COUNT(*) as total_memories,
                        MAX(updated_at) as last_updated,
                        SUM(event_count) as total_events
                    FROM memories 
                    WHERE agent_id = ?
                """, [agent_id]).fetchone()
                
                return {
                    'agent_id': agent_id,
                    'total_memories': stats_row['total_memories'],
                    'last_updated': stats_row['last_updated'],
                    'total_events': stats_row['total_events'] or 0
                }
                
        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        pass
    
    # ========== Conversation Recording Methods ==========
    
    def save_conversation(
        self, 
        agent_id: str, 
        conversation: List[Dict[str, str]], 
        memory_id: Optional[str] = None,
        session_id: Optional[str] = None,
        pipeline_result: Optional[Dict] = None
    ) -> str:
        """
        Save conversation to database.
        
        Args:
            agent_id: Agent ID
            conversation: List of conversation messages
            memory_id: Associated memory ID (optional)
            session_id: Session identifier (optional)
            pipeline_result: Pipeline execution results (optional)
            
        Returns:
            str: Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Save conversation record
                conn.execute("""
                    INSERT INTO conversations 
                    (conversation_id, agent_id, created_at, conversation_data, 
                     pipeline_result, memory_id, session_id, turn_count, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    conversation_id,
                    agent_id,
                    current_time,
                    json.dumps(conversation),
                    json.dumps(pipeline_result) if pipeline_result else None,
                    memory_id,
                    session_id or str(uuid.uuid4()),
                    len(conversation),
                    self._generate_conversation_summary(conversation)
                ])
                
                # Save individual messages
                for idx, message in enumerate(conversation):
                    message_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO conversation_messages 
                        (message_id, conversation_id, role, content, message_index, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        message_id,
                        conversation_id,
                        message.get('role', 'unknown'),
                        message.get('content', ''),
                        idx,
                        current_time
                    ])
                
                conn.commit()
                return conversation_id
                
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return ""
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict: Conversation data or None
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
                    SELECT role, content, message_index 
                    FROM conversation_messages 
                    WHERE conversation_id = ? 
                    ORDER BY message_index
                """, [conversation_id]).fetchall()
                
                return {
                    "conversation_id": conv_row["conversation_id"],
                    "agent_id": conv_row["agent_id"],
                    "created_at": conv_row["created_at"],
                    "messages": [dict(row) for row in message_rows],
                    "turn_count": conv_row["turn_count"],
                    "summary": conv_row["summary"],
                    "memory_id": conv_row["memory_id"],
                    "session_id": conv_row["session_id"]
                }
                
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None
    
    def get_conversations_by_agent(
        self, 
        agent_id: str, 
        limit: int = 20,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversations for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of conversations
            session_id: Filter by session ID (optional)
            
        Returns:
            List[Dict]: List of conversations
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                    SELECT conversation_id, created_at, turn_count, summary, session_id, memory_id
                    FROM conversations 
                    WHERE agent_id = ?
                """
                params = [agent_id]
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []
    
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
    
    def _generate_conversation_summary(self, conversation: List[Dict[str, str]]) -> str:
        """Generate a simple summary of the conversation."""
        if not conversation:
            return ""
        
        # Simple summary: first user message + turn count
        first_user_msg = next(
            (msg['content'][:100] for msg in conversation if msg.get('role') == 'user'), 
            "No user message"
        )
        
        return f"Conversation with {len(conversation)} turns: {first_user_msg}..." 