"""
Database module for PersonaLab memory persistence.

This module provides SQLite-based storage for the Memory system.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from .memory import Memory, UserMemory, AgentMemory, ProfileMemory, EventMemory


class MemoryDatabase:
    """
    SQLite database for persisting Memory system data.
    """
    
    def __init__(self, db_path: Union[str, Path] = "personalab_memory.db"):
        """
        Initialize the memory database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Users table  
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (agent_id, user_id),
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                )
            """)
            
            # Profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    profile_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (agent_id, user_id),
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                )
            """)
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                )
            """)
            
            conn.commit()
    
    def save_memory(self, memory: Memory) -> None:
        """
        Save complete Memory instance to database.
        
        Args:
            memory: Memory instance to save
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Save agent
            cursor.execute("""
                INSERT OR REPLACE INTO agents (agent_id, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (memory.agent_id, current_time, current_time))
            
            # Save agent memory
            self._save_agent_memory(cursor, memory.agent_memory, current_time)
            
            # Save user memories
            for user_id, user_memory in memory._user_memories.items():
                self._save_user_memory(cursor, user_memory, current_time)
            
            conn.commit()
    
    def _save_agent_memory(self, cursor: sqlite3.Cursor, agent_memory: AgentMemory, current_time: str) -> None:
        """Save agent memory to database."""
        agent_id = agent_memory.agent_id
        user_id = "0"  # Agent uses "0" as user_id
        
        # Save agent profile
        cursor.execute("""
            INSERT OR REPLACE INTO profiles (agent_id, user_id, profile_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, user_id, agent_memory.profile.get_profile(), current_time, current_time))
        
        # Clear existing agent events
        cursor.execute("DELETE FROM events WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        
        # Save agent events
        for event in agent_memory.events._memories:
            cursor.execute("""
                INSERT INTO events (agent_id, user_id, event_content, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, user_id, event, current_time, current_time))
    
    def _save_user_memory(self, cursor: sqlite3.Cursor, user_memory: UserMemory, current_time: str) -> None:
        """Save user memory to database."""
        agent_id = user_memory.agent_id
        user_id = user_memory.user_id
        
        # Save user record
        cursor.execute("""
            INSERT OR REPLACE INTO users (agent_id, user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (agent_id, user_id, current_time, current_time))
        
        # Save user profile
        cursor.execute("""
            INSERT OR REPLACE INTO profiles (agent_id, user_id, profile_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, user_id, user_memory.profile.get_profile(), current_time, current_time))
        
        # Clear existing user events
        cursor.execute("DELETE FROM events WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        
        # Save user events
        for event in user_memory.events._memories:
            cursor.execute("""
                INSERT INTO events (agent_id, user_id, event_content, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, user_id, event, current_time, current_time))
    
    def load_memory(self, agent_id: str) -> Optional[Memory]:
        """
        Load Memory instance from database.
        
        Args:
            agent_id: Agent ID to load
            
        Returns:
            Memory instance or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if agent exists
            cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
            agent_row = cursor.fetchone()
            if not agent_row:
                return None
            
            # Create Memory instance
            memory = Memory(agent_id)
            
            # Load agent memory
            self._load_agent_memory(cursor, memory.agent_memory)
            
            # Load user memories
            cursor.execute("SELECT user_id FROM users WHERE agent_id = ?", (agent_id,))
            user_rows = cursor.fetchall()
            
            for (user_id,) in user_rows:
                user_memory = memory.get_user_memory(user_id)
                self._load_user_memory(cursor, user_memory)
            
            return memory
    
    def _load_agent_memory(self, cursor: sqlite3.Cursor, agent_memory: AgentMemory) -> None:
        """Load agent memory from database."""
        agent_id = agent_memory.agent_id
        user_id = "0"
        
        # Load agent profile
        cursor.execute("SELECT profile_data FROM profiles WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        profile_row = cursor.fetchone()
        if profile_row:
            agent_memory.profile.set_profile(profile_row[0])
        
        # Load agent events
        cursor.execute("""
            SELECT event_content FROM events 
            WHERE agent_id = ? AND user_id = ? 
            ORDER BY id
        """, (agent_id, user_id))
        event_rows = cursor.fetchall()
        
        agent_memory.events._memories = [event[0] for event in event_rows]
    
    def _load_user_memory(self, cursor: sqlite3.Cursor, user_memory: UserMemory) -> None:
        """Load user memory from database."""
        agent_id = user_memory.agent_id
        user_id = user_memory.user_id
        
        # Load user profile
        cursor.execute("SELECT profile_data FROM profiles WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        profile_row = cursor.fetchone()
        if profile_row:
            user_memory.profile.set_profile(profile_row[0])
        
        # Load user events
        cursor.execute("""
            SELECT event_content FROM events 
            WHERE agent_id = ? AND user_id = ? 
            ORDER BY id
        """, (agent_id, user_id))
        event_rows = cursor.fetchall()
        
        user_memory.events._memories = [event[0] for event in event_rows]
    
    def list_agents(self) -> List[str]:
        """Get list of all agent IDs in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT agent_id FROM agents ORDER BY agent_id")
            return [row[0] for row in cursor.fetchall()]
    
    def list_users(self, agent_id: str) -> List[str]:
        """Get list of user IDs for a specific agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE agent_id = ? ORDER BY user_id", (agent_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete agent and all associated data.
        
        Args:
            agent_id: Agent ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if agent exists
            cursor.execute("SELECT 1 FROM agents WHERE agent_id = ?", (agent_id,))
            if not cursor.fetchone():
                return False
            
            # Delete in order (foreign keys)
            cursor.execute("DELETE FROM events WHERE agent_id = ?", (agent_id,))
            cursor.execute("DELETE FROM profiles WHERE agent_id = ?", (agent_id,))
            cursor.execute("DELETE FROM users WHERE agent_id = ?", (agent_id,))
            cursor.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
            
            conn.commit()
            return True
    
    def delete_user(self, agent_id: str, user_id: str) -> bool:
        """
        Delete user and associated data.
        
        Args:
            agent_id: Agent ID
            user_id: User ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT 1 FROM users WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
            if not cursor.fetchone():
                return False
            
            # Delete user data
            cursor.execute("DELETE FROM events WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
            cursor.execute("DELETE FROM profiles WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
            cursor.execute("DELETE FROM users WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
            
            conn.commit()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM agents")
            agent_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM profiles")
            profile_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]
            
            return {
                "agents": agent_count,
                "users": user_count, 
                "profiles": profile_count,
                "events": event_count,
                "database_file": str(self.db_path),
                "database_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0
            }


class PersistentMemory(Memory):
    """
    Memory class with automatic database persistence.
    """
    
    def __init__(self, agent_id: str, db_path: Union[str, Path] = "personalab_memory.db", auto_save: bool = True):
        """
        Initialize persistent memory.
        
        Args:
            agent_id: Agent identifier
            db_path: Database file path
            auto_save: Whether to automatically save changes
        """
        self.db = MemoryDatabase(db_path)
        self.auto_save = auto_save
        
        # Try to load existing data
        existing_memory = self.db.load_memory(agent_id)
        if existing_memory:
            # Copy data from loaded memory
            super().__init__(agent_id)
            self.agent_memory = existing_memory.agent_memory
            self._user_memories = existing_memory._user_memories
        else:
            # Create new memory
            super().__init__(agent_id)
            if auto_save:
                self.save()
    
    def save(self) -> None:
        """Save memory to database."""
        self.db.save_memory(self)
    
    def get_user_memory(self, user_id: str) -> UserMemory:
        """Get user memory with auto-save support."""
        user_memory = super().get_user_memory(user_id)
        if self.auto_save:
            self.save()
        return PersistentUserMemory(user_memory, self)
    
    def get_agent_memory(self) -> 'PersistentAgentMemory':
        """Get agent memory with auto-save support."""
        return PersistentAgentMemory(super().get_agent_memory(), self)
    
    def __del__(self):
        """Save on destruction if auto_save is enabled."""
        if hasattr(self, 'auto_save') and self.auto_save:
            try:
                self.save()
            except:
                pass  # Ignore errors during destruction


class PersistentUserMemory:
    """UserMemory wrapper with auto-save functionality."""
    
    def __init__(self, user_memory: UserMemory, persistent_memory: PersistentMemory):
        self._user_memory = user_memory
        self._persistent_memory = persistent_memory
        self.agent_id = user_memory.agent_id
        self.user_id = user_memory.user_id
    
    @property
    def profile(self) -> 'PersistentProfileMemory':
        """Get profile with auto-save."""
        return PersistentProfileMemory(self._user_memory.profile, self._persistent_memory)
    
    @property
    def events(self) -> 'PersistentEventMemory':
        """Get events with auto-save."""
        return PersistentEventMemory(self._user_memory.events, self._persistent_memory)
    
    def __str__(self) -> str:
        return str(self._user_memory)


class PersistentAgentMemory:
    """AgentMemory wrapper with auto-save functionality."""
    
    def __init__(self, agent_memory: AgentMemory, persistent_memory: PersistentMemory):
        self._agent_memory = agent_memory
        self._persistent_memory = persistent_memory
        self.agent_id = agent_memory.agent_id
    
    @property
    def profile(self) -> 'PersistentProfileMemory':
        """Get profile with auto-save."""
        return PersistentProfileMemory(self._agent_memory.profile, self._persistent_memory)
    
    @property
    def events(self) -> 'PersistentEventMemory':
        """Get events with auto-save."""
        return PersistentEventMemory(self._agent_memory.events, self._persistent_memory)
    
    def __str__(self) -> str:
        return str(self._agent_memory)


class PersistentProfileMemory:
    """ProfileMemory wrapper with auto-save functionality."""
    
    def __init__(self, profile_memory: ProfileMemory, persistent_memory: PersistentMemory):
        self._profile_memory = profile_memory
        self._persistent_memory = persistent_memory
    
    def get_profile(self) -> str:
        """Get profile data."""
        return self._profile_memory.get_profile()
    
    def set_profile(self, profile_data: str) -> None:
        """Set profile data and auto-save."""
        self._profile_memory.set_profile(profile_data)
        if self._persistent_memory.auto_save:
            self._persistent_memory.save()
    
    def clear(self) -> None:
        """Clear profile and auto-save."""
        self._profile_memory.clear()
        if self._persistent_memory.auto_save:
            self._persistent_memory.save()
    
    def get_size(self) -> int:
        """Get profile size."""
        return self._profile_memory.get_size()
    
    def __str__(self) -> str:
        return str(self._profile_memory)


class PersistentEventMemory:
    """EventMemory wrapper with auto-save functionality."""
    
    def __init__(self, event_memory: EventMemory, persistent_memory: PersistentMemory):
        self._event_memory = event_memory
        self._persistent_memory = persistent_memory
    
    def add_memory(self, content: str) -> str:
        """Add memory and auto-save."""
        result = self._event_memory.add_memory(content)
        if self._persistent_memory.auto_save:
            self._persistent_memory.save()
        return result
    
    def get_memories(self, limit: Optional[int] = None) -> List[str]:
        """Get memories."""
        return self._event_memory.get_memories(limit)
    
    def get_recent_memories(self, limit: int = 10) -> List[str]:
        """Get recent memories."""
        return self._event_memory.get_recent_memories(limit)
    
    def search_memories(self, query: str, case_sensitive: bool = False) -> List[str]:
        """Search memories."""
        return self._event_memory.search_memories(query, case_sensitive)
    
    def get_memories_count(self) -> int:
        """Get memory count."""
        return self._event_memory.get_memories_count()
    
    def clear(self) -> None:
        """Clear memories and auto-save."""
        self._event_memory.clear()
        if self._persistent_memory.auto_save:
            self._persistent_memory.save()
    
    def get_size(self) -> int:
        """Get memory size."""
        return self._event_memory.get_size()
    
    def __str__(self) -> str:
        return str(self._event_memory) 