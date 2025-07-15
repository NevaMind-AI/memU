"""
Database Manager for Memory Operations

This module provides database-based memory management for character profiles and events.
Uses PostgreSQL + pgvector for storage with embedding support for semantic search.
"""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
import numpy as np

from ..utils import get_logger
from ..db.utils import build_connection_string, get_db_connection
from ..db.pg_storage import PostgreSQLStorageBase

logger = get_logger(__name__)


class MemoryDatabaseManager(PostgreSQLStorageBase):
    """
    Database-based memory management for character profiles and events.
    
    Uses PostgreSQL + pgvector to store:
    - Character profiles (markdown content + embeddings)
    - Character events (markdown content + embeddings) 
    - Supports semantic search via vector similarity
    """
    
    def __init__(self, connection_string: Optional[str] = None, **kwargs):
        """
        Initialize Memory Database Manager
        
        Args:
            connection_string: PostgreSQL connection string
            **kwargs: Connection parameters (host, port, dbname, user, password)
        """
        super().__init__(connection_string, **kwargs)
        self.embedding_client = None
        
        logger.info("MemoryDatabaseManager initialized with PostgreSQL + pgvector")
    
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

                FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE ON UPDATE CASCADE,
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
        
        # Add composite indexes for common memory query patterns
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_contents_type_vector_filtered
            ON memory_contents (content_type, content_id) 
            WHERE content_vector IS NOT NULL
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_agent_user_updated
            ON memories (agent_id, user_id, updated_at DESC)
        """
        )
    
    def set_embedding_client(self, embedding_client):
        """Set the embedding client for generating vectors"""
        self.embedding_client = embedding_client
        logger.info("Embedding client set for vector generation")
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text content"""
        if not self.embedding_client:
            logger.warning("No embedding client set, skipping vector generation")
            return None
        
        try:
            # Assume embedding client has an embed method
            if hasattr(self.embedding_client, 'embed'):
                embedding = self.embedding_client.embed(text)
                return embedding if isinstance(embedding, list) else embedding.tolist()
            elif hasattr(self.embedding_client, 'get_embedding'):
                embedding = self.embedding_client.get_embedding(text)
                return embedding if isinstance(embedding, list) else embedding.tolist()
            else:
                logger.error("Embedding client does not have embed() or get_embedding() method")
                return None
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _get_memory_id(self, character_name: str) -> str:
        """Get or create memory_id for a character"""
        # Use character name as agent_id, and default user for simplicity
        agent_id = character_name.lower()
        user_id = "default"
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if memory exists
                cur.execute(
                    "SELECT memory_id FROM memories WHERE agent_id = %s AND user_id = %s",
                    (agent_id, user_id)
                )
                result = cur.fetchone()
                
                if result:
                    return result[0]
                
                # Create new memory record
                memory_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO memories (memory_id, agent_id, user_id, created_at, updated_at, version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (memory_id, agent_id, user_id, datetime.now(), datetime.now(), 3)
                )
                conn.commit()  # Commit the transaction
                return memory_id
    
    def _content_hash(self, content: str) -> str:
        """Generate hash for content to detect changes"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _save_content(self, memory_id: str, content_type: str, content: str) -> bool:
        """Save content to memory_contents table with embedding"""
        try:
            content_hash = self._content_hash(content)
            content_vector = self._generate_embedding(content)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if content already exists and hasn't changed
                    cur.execute(
                        """
                        SELECT content_hash FROM memory_contents 
                        WHERE memory_id = %s AND content_type = %s
                        """,
                        (memory_id, content_type)
                    )
                    existing = cur.fetchone()
                    
                    if existing and existing[0] == content_hash:
                        logger.debug(f"Content unchanged for {content_type}, skipping save")
                        return True
                    
                    # Prepare content data
                    content_data = {
                        "content": content,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # Insert or update content
                    cur.execute(
                        """
                        INSERT INTO memory_contents 
                        (content_id, memory_id, content_type, content_data, content_text, 
                         content_hash, content_vector, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (memory_id, content_type) 
                        DO UPDATE SET
                            content_data = EXCLUDED.content_data,
                            content_text = EXCLUDED.content_text,
                            content_hash = EXCLUDED.content_hash,
                            content_vector = EXCLUDED.content_vector,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            str(uuid.uuid4()),
                            memory_id,
                            content_type,
                            json.dumps(content_data),
                            content,
                            content_hash,
                            content_vector,
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    
                    # Update memories table timestamp
                    cur.execute(
                        "UPDATE memories SET updated_at = %s WHERE memory_id = %s",
                        (datetime.now(), memory_id)
                    )
                    
                    conn.commit()  # Explicitly commit the transaction
                    
            logger.debug(f"Saved {content_type} content for memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving {content_type} content: {e}")
            return False
    
    def _load_content(self, memory_id: str, content_type: str) -> str:
        """Load content from memory_contents table"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT content_text FROM memory_contents 
                        WHERE memory_id = %s AND content_type = %s
                        """,
                        (memory_id, content_type)
                    )
                    result = cur.fetchone()
                    
                    if result:
                        return result[0] or ""
                    return ""
                    
        except Exception as e:
            logger.error(f"Error loading {content_type} content: {e}")
            return ""
    
    def read_profile(self, character_name: str) -> str:
        """
        Read character profile from database
        
        Args:
            character_name: Name of the character
            
        Returns:
            str: Profile content in markdown format
        """
        try:
            memory_id = self._get_memory_id(character_name)
            content = self._load_content(memory_id, "profile")
            logger.debug(f"Read profile for {character_name}: {len(content)} chars")
            return content
        except Exception as e:
            logger.error(f"Error reading profile for {character_name}: {e}")
            return ""
    
    def write_profile(self, character_name: str, content: str) -> bool:
        """
        Write character profile to database with embedding
        
        Args:
            character_name: Name of the character
            content: Profile content in markdown format
            
        Returns:
            bool: Whether write was successful
        """
        try:
            # Use agent_id and user_id
            agent_id = character_name.lower()
            user_id = "default"
            
            content_hash = self._content_hash(content)
            content_vector = self._generate_embedding(content)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get or create memory
                    cur.execute(
                        "SELECT memory_id FROM memories WHERE agent_id = %s AND user_id = %s",
                        (agent_id, user_id)
                    )
                    result = cur.fetchone()
                    
                    if result:
                        memory_id = result[0]
                    else:
                        # Create new memory record
                        memory_id = str(uuid.uuid4())
                        cur.execute(
                            """
                            INSERT INTO memories (memory_id, agent_id, user_id, created_at, updated_at, version)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (memory_id, agent_id, user_id, datetime.now(), datetime.now(), 3)
                        )
                    
                    # Save content
                    content_data = {
                        "content": content,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    cur.execute(
                        """
                        INSERT INTO memory_contents 
                        (content_id, memory_id, content_type, content_data, content_text, 
                         content_hash, content_vector, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (memory_id, content_type) 
                        DO UPDATE SET
                            content_data = EXCLUDED.content_data,
                            content_text = EXCLUDED.content_text,
                            content_hash = EXCLUDED.content_hash,
                            content_vector = EXCLUDED.content_vector,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            str(uuid.uuid4()),
                            memory_id,
                            "profile",
                            json.dumps(content_data),
                            content,
                            content_hash,
                            content_vector,
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    
                    # Update memories table timestamp
                    cur.execute(
                        "UPDATE memories SET updated_at = %s WHERE memory_id = %s",
                        (datetime.now(), memory_id)
                    )
                    
                    conn.commit()
            
            logger.info(f"Profile written for {character_name}: {len(content)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Error writing profile for {character_name}: {e}")
            return False
    
    def read_events(self, character_name: str) -> str:
        """
        Read character events from database
        
        Args:
            character_name: Name of the character
            
        Returns:
            str: Events content in markdown format
        """
        try:
            memory_id = self._get_memory_id(character_name)
            content = self._load_content(memory_id, "event")
            logger.debug(f"Read events for {character_name}: {len(content)} chars")
            return content
        except Exception as e:
            logger.error(f"Error reading events for {character_name}: {e}")
            return ""
    
    def write_events(self, character_name: str, content: str) -> bool:
        """
        Write character events to database with embedding
        
        Args:
            character_name: Name of the character
            content: Events content in markdown format
            
        Returns:
            bool: Whether write was successful
        """
        try:
            # Use agent_id and user_id
            agent_id = character_name.lower()
            user_id = "default"
            
            content_hash = self._content_hash(content)
            content_vector = self._generate_embedding(content)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get or create memory
                    cur.execute(
                        "SELECT memory_id FROM memories WHERE agent_id = %s AND user_id = %s",
                        (agent_id, user_id)
                    )
                    result = cur.fetchone()
                    
                    if result:
                        memory_id = result[0]
                    else:
                        # Create new memory record
                        memory_id = str(uuid.uuid4())
                        cur.execute(
                            """
                            INSERT INTO memories (memory_id, agent_id, user_id, created_at, updated_at, version)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (memory_id, agent_id, user_id, datetime.now(), datetime.now(), 3)
                        )
                    
                    # Save content
                    content_data = {
                        "content": content,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    cur.execute(
                        """
                        INSERT INTO memory_contents 
                        (content_id, memory_id, content_type, content_data, content_text, 
                         content_hash, content_vector, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (memory_id, content_type) 
                        DO UPDATE SET
                            content_data = EXCLUDED.content_data,
                            content_text = EXCLUDED.content_text,
                            content_hash = EXCLUDED.content_hash,
                            content_vector = EXCLUDED.content_vector,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            str(uuid.uuid4()),
                            memory_id,
                            "event",
                            json.dumps(content_data),
                            content,
                            content_hash,
                            content_vector,
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    
                    # Update memories table timestamp
                    cur.execute(
                        "UPDATE memories SET updated_at = %s WHERE memory_id = %s",
                        (datetime.now(), memory_id)
                    )
                    
                    conn.commit()
            
            logger.info(f"Events written for {character_name}: {len(content)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Error writing events for {character_name}: {e}")
            return False
    
    def append_events(self, character_name: str, new_events: str) -> bool:
        """
        Append new events to existing events in database
        
        Args:
            character_name: Name of the character
            new_events: New events to append
            
        Returns:
            bool: Whether append was successful
        """
        try:
            existing_events = self.read_events(character_name)
            if existing_events:
                combined_events = existing_events + "\n\n" + new_events
            else:
                combined_events = new_events
            
            return self.write_events(character_name, combined_events)
            
        except Exception as e:
            logger.error(f"Error appending events for {character_name}: {e}")
            return False
    
    def list_characters(self) -> List[str]:
        """
        List all characters in database
        
        Returns:
            List[str]: List of character names
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT agent_id FROM memories 
                        ORDER BY agent_id
                        """
                    )
                    results = cur.fetchall()
                    characters = [row[0] for row in results]
                    logger.debug(f"Found {len(characters)} characters in database")
                    return characters
                    
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            return []
    
    def clear_character_memory(self, character_name: str) -> bool:
        """
        Clear all memory for a character from database
        
        Args:
            character_name: Name of the character
            
        Returns:
            bool: Whether clear was successful
        """
        try:
            agent_id = character_name.lower()
            user_id = "default"
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Delete from memories table (cascade will delete memory_contents)
                    cur.execute(
                        "DELETE FROM memories WHERE agent_id = %s AND user_id = %s",
                        (agent_id, user_id)
                    )
                    deleted_count = cur.rowcount
                    
            if deleted_count > 0:
                logger.info(f"Cleared memory for character: {character_name}")
                return True
            else:
                logger.warning(f"No memory found for character: {character_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error clearing memory for {character_name}: {e}")
            return False
    
    def get_character_info(self, character_name: str) -> Dict[str, Any]:
        """
        Get character memory information from database
        
        Args:
            character_name: Name of the character
            
        Returns:
            Dict with character memory information
        """
        try:
            agent_id = character_name.lower()
            user_id = "default"
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get memory metadata
                    cur.execute(
                        """
                        SELECT memory_id, created_at, updated_at 
                        FROM memories 
                        WHERE agent_id = %s AND user_id = %s
                        """,
                        (agent_id, user_id)
                    )
                    memory_result = cur.fetchone()
                    
                    if not memory_result:
                        return {
                            "character_name": character_name,
                            "exists": False
                        }
                    
                    memory_id = memory_result[0]
                    created_at = memory_result[1]
                    updated_at = memory_result[2]
                    
                    # Get content info
                    cur.execute(
                        """
                        SELECT content_type, 
                               LENGTH(content_text) as content_length,
                               updated_at as content_updated,
                               (content_vector IS NOT NULL) as has_embedding
                        FROM memory_contents 
                        WHERE memory_id = %s
                        ORDER BY content_type
                        """,
                        (memory_id,)
                    )
                    content_results = cur.fetchall()
                    
                    content_info = {}
                    for row in content_results:
                        content_info[row[0]] = {
                            "length": row[1],
                            "updated_at": row[2].isoformat() if row[2] else None,
                            "has_embedding": row[3]
                        }
                    
                    return {
                        "character_name": character_name,
                        "exists": True,
                        "memory_id": memory_id,
                        "created_at": created_at.isoformat() if created_at else None,
                        "updated_at": updated_at.isoformat() if updated_at else None,
                        "content": content_info
                    }
                    
        except Exception as e:
            logger.error(f"Error getting character info for {character_name}: {e}")
            return {
                "character_name": character_name,
                "exists": False,
                "error": str(e)
            }
    
    def search_similar_content(self, query: str, content_type: Optional[str] = None, 
                             character_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity
        
        Args:
            query: Search query text
            content_type: Filter by content type ('profile', 'event', 'mind')
            character_name: Filter by character name
            limit: Maximum number of results
            
        Returns:
            List of similar content results with similarity scores
        """
        try:
            # Generate query embedding
            query_vector = self._generate_embedding(query)
            if not query_vector:
                logger.warning("Could not generate embedding for query, falling back to text search")
                return self._text_search(query, content_type, character_name, limit)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Build query with optional filters
                    where_conditions = ["mc.content_vector IS NOT NULL"]
                    params = [query_vector, limit]
                    
                    if content_type:
                        where_conditions.append("mc.content_type = %s")
                        params.insert(-1, content_type)
                    
                    if character_name:
                        where_conditions.append("m.agent_id = %s")
                        params.insert(-1, character_name.lower())
                    
                    where_clause = " AND ".join(where_conditions)
                    
                    query_sql = f"""
                        SELECT 
                            m.agent_id as character_name,
                            mc.content_type,
                            mc.content_text,
                            mc.updated_at,
                            (mc.content_vector <=> %s) as similarity_distance,
                            (1 - (mc.content_vector <=> %s)) as similarity_score
                        FROM memories m
                        JOIN memory_contents mc ON m.memory_id = mc.memory_id
                        WHERE {where_clause}
                        ORDER BY mc.content_vector <=> %s
                        LIMIT %s
                    """
                    
                    # Add query vector for each occurrence in the SQL
                    full_params = [query_vector, query_vector] + params + [query_vector]
                    
                    cur.execute(query_sql, full_params)
                    results = cur.fetchall()
                    
                    formatted_results = []
                    for row in results:
                        formatted_results.append({
                            "character_name": row[0],
                            "content_type": row[1],
                            "content": row[2][:500] + "..." if len(row[2]) > 500 else row[2],
                            "updated_at": row[3].isoformat() if row[3] else None,
                            "similarity_distance": float(row[4]),
                            "similarity_score": float(row[5])
                        })
                    
                    logger.debug(f"Vector search found {len(formatted_results)} similar content items")
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"Error in vector similarity search: {e}")
            # Fallback to text search
            return self._text_search(query, content_type, character_name, limit)
    
    def _text_search(self, query: str, content_type: Optional[str] = None, 
                    character_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback text search when vector search is not available"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    where_conditions = ["mc.content_text ILIKE %s"]
                    params = [f"%{query}%"]
                    
                    if content_type:
                        where_conditions.append("mc.content_type = %s")
                        params.append(content_type)
                    
                    if character_name:
                        where_conditions.append("m.agent_id = %s")
                        params.append(character_name.lower())
                    
                    params.append(limit)
                    where_clause = " AND ".join(where_conditions)
                    
                    query_sql = f"""
                        SELECT 
                            m.agent_id as character_name,
                            mc.content_type,
                            mc.content_text,
                            mc.updated_at
                        FROM memories m
                        JOIN memory_contents mc ON m.memory_id = mc.memory_id
                        WHERE {where_clause}
                        ORDER BY mc.updated_at DESC
                        LIMIT %s
                    """
                    
                    cur.execute(query_sql, params)
                    results = cur.fetchall()
                    
                    formatted_results = []
                    for row in results:
                        formatted_results.append({
                            "character_name": row[0],
                            "content_type": row[1],
                            "content": row[2][:500] + "..." if len(row[2]) > 500 else row[2],
                            "updated_at": row[3].isoformat() if row[3] else None,
                            "similarity_score": 0.0  # Text search doesn't provide similarity score
                        })
                    
                    logger.debug(f"Text search found {len(formatted_results)} matching content items")
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            return [] 