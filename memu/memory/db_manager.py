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
    
    def set_embedding_client(self, embedding_client):
        """Set the embedding client for generating vectors"""
        self.embedding_client = embedding_client
        logger.info("Embedding client set for vector generation")
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using the embedding client"""
        if not self.embedding_client:
            logger.warning("No embedding client set, skipping embedding generation")
            return None
            
        try:
            embedding = self.embedding_client.get_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def read_profile(self, character_name: str) -> str:
        """
        Read character profile from database
        
        Args:
            character_name: Name of the character
            
        Returns:
            str: Profile content or empty string if not found
        """
        try:
            agent_id = character_name.lower()
            user_id = "default"
            category = "profile"
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT content FROM memories 
                        WHERE agent_id = %s AND user_id = %s AND category = %s
                        """,
                        (agent_id, user_id, category)
                    )
                    result = cur.fetchone()
                    
                    if result:
                        return result[0] or ""
                    return ""
                    
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
            category = "profile"
            
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            memory_embedding = self._generate_embedding(content)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if profile already exists
                    cur.execute(
                        "SELECT id FROM memories WHERE agent_id = %s AND user_id = %s AND category = %s",
                        (agent_id, user_id, category)
                    )
                    result = cur.fetchone()
                    
                    if result:
                        # Update existing record
                        cur.execute(
                            """
                            UPDATE memories
                            SET content = %s, embedding = %s, updated_at = %s
                            WHERE id = %s
                            """,
                            (content, memory_embedding, datetime.now(), result[0])
                        )
                    else:
                        # Insert new record
                        memory_id = str(uuid.uuid4())
                        cur.execute(
                            """
                            INSERT INTO memories
                            (id, agent_id, user_id, category, content, embedding, 
                             created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                memory_id,
                                agent_id,
                                user_id,
                                category,
                                content,
                                memory_embedding,
                                datetime.now(),
                                datetime.now()
                            )
                        )
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error writing profile for {character_name}: {e}")
            return False

    def read_event(self, character_name: str) -> str:
        """
        Read character events from database
        
        Args:
            character_name: Name of the character
            
        Returns:
            str: Combined events content or empty string if not found
        """
        try:
            agent_id = character_name.lower()
            user_id = "default"
            category = "event"
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT content FROM memories 
                        WHERE agent_id = %s AND user_id = %s AND category = %s
                        ORDER BY created_at ASC
                        """,
                        (agent_id, user_id, category)
                    )
                    results = cur.fetchall()
                    
                    if results:
                        # Combine all event contents
                        events = [result[0] for result in results if result[0]]
                        return "\n\n".join(events)
                    return ""
                    
        except Exception as e:
            logger.error(f"Error reading events for {character_name}: {e}")
            return ""

    def write_event(self, character_name: str, content: str) -> bool:
        """
        Write character event to database with embedding
        
        Args:
            character_name: Name of the character
            content: Event content in markdown format
            
        Returns:
            bool: Whether write was successful
        """
        try:
            # Use agent_id and user_id
            agent_id = character_name.lower()
            user_id = "default"
            category = "event"
            
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            memory_embedding = self._generate_embedding(content)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if event already exists (though events typically accumulate)
                    # For events, we usually want to append/insert new ones rather than update
                    memory_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO memories
                        (id, agent_id, user_id, category, content, embedding, 
                         created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            memory_id,
                            agent_id,
                            user_id,
                            category,
                            content,
                            memory_embedding,
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error writing event for {character_name}: {e}")
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
            existing_events = self.read_event(character_name)
            if existing_events:
                combined_events = existing_events + "\n\n" + new_events
            else:
                combined_events = new_events
            
            return self.write_event(character_name, combined_events)
            
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
        Get detailed information about a character's memory
        
        Args:
            character_name: Name of the character
            
        Returns:
            Dictionary with character memory information
        """
        try:
            agent_id = character_name.lower()
            user_id = "default"
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get character memory stats
                    cur.execute(
                        """
                        SELECT category,
                               COUNT(*) as count,
                               MAX(created_at) as created_at,
                               MAX(updated_at) as updated_at,
                               SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as has_embedding_count
                        FROM memories 
                        WHERE agent_id = %s AND user_id = %s
                        GROUP BY category
                        ORDER BY category
                        """,
                        (agent_id, user_id)
                    )
                    category_results = cur.fetchall()
                    
                    category_info = {}
                    for row in category_results:
                        category_info[row[0]] = {
                            "count": row[1],
                            "created_at": row[2].isoformat() if row[2] else None,
                            "updated_at": row[3].isoformat() if row[3] else None,
                            "has_embedding": row[4] > 0
                        }
                    
                    # Get overall stats
                    cur.execute(
                        """
                        SELECT COUNT(*) as total_count,
                               MIN(created_at) as first_created,
                               MAX(updated_at) as last_updated
                        FROM memories 
                        WHERE agent_id = %s AND user_id = %s
                        """,
                        (agent_id, user_id)
                    )
                    overall_result = cur.fetchone()
                    
                    exists = overall_result[0] > 0 if overall_result else False
                    
                    return {
                        "character_name": character_name,
                        "exists": exists,
                        "total_memories": overall_result[0] if overall_result else 0,
                        "first_created": overall_result[1].isoformat() if overall_result and overall_result[1] else None,
                        "last_updated": overall_result[2].isoformat() if overall_result and overall_result[2] else None,
                        "categories": category_info
                    }
                    
        except Exception as e:
            logger.error(f"Error getting character info for {character_name}: {e}")
            return {
                "character_name": character_name,
                "exists": False,
                "error": str(e)
            }

    def search_similar_content(self, query: str, category: Optional[str] = None, 
                             character_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity
        
        Args:
            query: Search query text
            category: Filter by category (e.g., 'activity', 'profile', 'event', 'reminder', etc.)
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
                return self._text_search(query, category, character_name, limit)
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Build query with optional filters
                    where_conditions = ["embedding IS NOT NULL"]
                    params = [query_vector, limit]
                    
                    if category:
                        where_conditions.append("category = %s")
                        params.insert(-1, category)
                    
                    if character_name:
                        where_conditions.append("agent_id = %s")
                        params.insert(-1, character_name.lower())
                    
                    where_clause = " AND ".join(where_conditions)
                    
                    query_sql = f"""
                        SELECT 
                            agent_id as character_name,
                            category,
                            content,
                            updated_at,
                            (embedding <=> %s) as similarity_distance,
                            (1 - (embedding <=> %s)) as similarity_score
                        FROM memories
                        WHERE {where_clause}
                        ORDER BY embedding <=> %s
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
                            "category": row[1],
                            "content": row[2],
                            "updated_at": row[3].isoformat() if row[3] else None,
                            "similarity_distance": float(row[4]),
                            "similarity_score": float(row[5])
                        })
                    
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

    def _text_search(self, query: str, category: Optional[str] = None, 
                    character_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fallback text search when vector search is not available
        
        Args:
            query: Search query text
            category: Filter by category
            character_name: Filter by character name
            limit: Maximum number of results
            
        Returns:
            List of text search results
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Build query with optional filters
                    where_conditions = ["content ILIKE %s"]
                    params = [f"%{query}%", limit]
                    
                    if category:
                        where_conditions.append("category = %s")
                        params.insert(-1, category)
                    
                    if character_name:
                        where_conditions.append("agent_id = %s")
                        params.insert(-1, character_name.lower())
                    
                    where_clause = " AND ".join(where_conditions)
                    
                    query_sql = f"""
                        SELECT 
                            agent_id as character_name,
                            category,
                            content,
                            updated_at
                        FROM memories
                        WHERE {where_clause}
                        ORDER BY updated_at DESC
                        LIMIT %s
                    """
                    
                    cur.execute(query_sql, params)
                    results = cur.fetchall()
                    
                    formatted_results = []
                    for row in results:
                        formatted_results.append({
                            "character_name": row[0],
                            "category": row[1],
                            "content": row[2],
                            "updated_at": row[3].isoformat() if row[3] else None,
                            "similarity_score": 0.5  # Default score for text search
                        })
                    
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            return [] 