"""
Memory database storage layer module.

Based on STRUCTURE.md design, implements database storage and management for Memory objects:
- memories table: stores Memory basic information and metadata
- memory_contents table: unified storage for profile and event contents
- supports complete Memory CRUD operations

Note: Conversation recording and embeddings are now handled by the memo module.
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
    
    Provides complete database storage and management functionality for Memory objects.
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
        """Initialize database table structure with improved schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints and WAL mode for better performance
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Create memories table (unified Memory table) with embedded content
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER DEFAULT 2,
                    
                    -- Embedded content for simplified access
                    profile_content TEXT,              -- Direct profile storage
                    event_content TEXT,                -- JSON array for events
                    tom_content TEXT,                  -- JSON array for ToM insights
                    
                    -- Theory of Mind analysis results
                    tom_metadata TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    
                    -- Memory statistics
                    profile_content_hash TEXT,
                    event_count INTEGER DEFAULT 0,
                    last_event_date TEXT,
                    
                    -- Schema versioning for migrations
                    schema_version INTEGER DEFAULT 2
                )
            """)
            
            # Create memory_contents table (for backward compatibility and search)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_contents (
                    content_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    content_type TEXT NOT NULL CHECK (content_type IN ('profile', 'event', 'tom')),
                    
                    -- Content data
                    content_data TEXT NOT NULL,
                    content_text TEXT,
                    content_hash TEXT,
                    
                    -- Metadata
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    
                    FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE,
                    UNIQUE(memory_id, content_type)
                )
            """)

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_schema_version ON memories(schema_version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_contents_memory_type ON memory_contents(memory_id, content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_contents_hash ON memory_contents(content_hash)")
            
            # Create trigger for automatic cascade deletion
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS cleanup_memory_contents
                AFTER DELETE ON memories
                BEGIN
                    DELETE FROM memory_contents WHERE memory_id = OLD.memory_id;
                END
            """)
            
            conn.commit()
            
            # Run schema migration if needed
            self._migrate_database_schema()
            
    def _migrate_database_schema(self):
        """Migrate database schema to latest version"""
        with sqlite3.connect(self.db_path) as conn:
            # Check current schema version
            try:
                version_result = conn.execute(
                    "SELECT MAX(schema_version) FROM memories WHERE schema_version IS NOT NULL"
                ).fetchone()
                current_version = version_result[0] if version_result and version_result[0] else 1
            except sqlite3.OperationalError:
                current_version = 1
            
            if current_version < 2:
                print("Migrating database schema to version 2...")
                try:
                    # Add new columns for embedded content
                    conn.execute("ALTER TABLE memories ADD COLUMN profile_content TEXT")
                    conn.execute("ALTER TABLE memories ADD COLUMN event_content TEXT") 
                    conn.execute("ALTER TABLE memories ADD COLUMN tom_content TEXT")
                    conn.execute("ALTER TABLE memories ADD COLUMN schema_version INTEGER DEFAULT 2")
                    
                    # Update existing records
                    conn.execute("UPDATE memories SET schema_version = 2 WHERE schema_version IS NULL")
                    conn.commit()
                    print("Database schema migration completed.")
                except sqlite3.OperationalError as e:
                    print(f"Schema migration warning: {e}")
                    # Columns may already exist
    
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
                    'tom_metadata': json.dumps(memory.mind_metadata) if memory.mind_metadata else None,
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
                    memory.mind_metadata = json.loads(memory_row['tom_metadata'])
                
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
        Delete Memory object with improved transaction handling.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            bool: Whether deletion was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Start transaction
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    # Check if memory exists
                    exists = conn.execute(
                        "SELECT 1 FROM memories WHERE memory_id = ?", 
                        [memory_id]
                    ).fetchone()
                    
                    if not exists:
                        conn.execute("ROLLBACK")
                        return False
                    
                    # Delete related content first to maintain referential integrity
                    content_result = conn.execute(
                        "DELETE FROM memory_contents WHERE memory_id = ?", 
                        [memory_id]
                    )
                    
                    # Delete main memory record
                    memory_result = conn.execute(
                        "DELETE FROM memories WHERE memory_id = ?", 
                        [memory_id]
                    )
                    
                    # Verify deletions
                    if memory_result.rowcount == 0:
                        conn.execute("ROLLBACK")
                        return False
                    
                    conn.execute("COMMIT")
                    return True
                    
                except Exception as e:
                    conn.execute("ROLLBACK")
                    print(f"Transaction failed during deletion: {e}")
                    return False
                
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False

    def _simplified_delete_memory(self, memory_id: str) -> bool:
        """
        Simplified deletion method using CASCADE constraints.
        This is the preferred approach for future database schema.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            bool: Whether deletion was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # With proper CASCADE constraints, we only need one operation
                result = conn.execute(
                    "DELETE FROM memories WHERE memory_id = ?", 
                    [memory_id]
                )
                
                return result.rowcount > 0
                
        except Exception as e:
            print(f"Error in simplified deletion: {e}")
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
    
 