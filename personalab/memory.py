"""
Memory management module for PersonaLab.

This module provides simplified string-based memory management for AI personas.
Memory is a container that manages both user and agent memories.
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class BaseMemory(ABC):
    """
    Abstract base class for all memory types.
    """
    
    def __init__(self, agent_id: str, user_id: str = "0"):
        """
        Initialize base memory for a specific agent and user combination.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only profiles)
        """
        self.agent_id = agent_id
        self.user_id = user_id
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _update_timestamp(self) -> None:
        """Update the last modification timestamp."""
        self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memory data."""
        pass
    
    @property
    def is_user_profile(self) -> bool:
        """Check if this is a user-specific profile."""
        return self.user_id != "0"
    
    @property
    def is_agent_profile(self) -> bool:
        """Check if this is an agent-only profile."""
        return self.user_id == "0"
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get general information about this memory instance."""
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "memory_type": self.__class__.__name__,
            "is_user_profile": self.is_user_profile,
            "is_agent_profile": self.is_agent_profile,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "size": self.get_size()
        }


class ProfileMemory(BaseMemory):
    """
    Manages persona profile information as a single string.
    """
    
    def __init__(self, agent_id: str, user_id: str = "0", profile_data: str = ""):
        """
        Initialize ProfileMemory.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only profiles)
            profile_data: Initial profile data as string
        """
        super().__init__(agent_id, user_id)
        self._profile: str = profile_data
    
    def get_profile(self) -> str:
        """Get complete profile data."""
        return self._profile
    
    def set_profile(self, profile_data: str) -> None:
        """Set profile data."""
        self._profile = str(profile_data)
        self._update_timestamp()
    
    def clear(self) -> None:
        """Clear all profile data."""
        self._profile = ""
        self._update_timestamp()
    
    def get_size(self) -> int:
        """Get length of profile string."""
        return len(self._profile)
    
    def __str__(self) -> str:
        profile_type = "user" if self.is_user_profile else "agent"
        return f"ProfileMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={profile_type}, length={len(self._profile)})"


class EventMemory(BaseMemory):
    """
    Manages simple string-based memories with datetime strings.
    No categories, no complex filtering - just content and time.
    """
    
    def __init__(self, agent_id: str, user_id: str = "0", max_memories: int = 1000):
        """
        Initialize EventMemory.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only memory)
            max_memories: Maximum number of memories to keep
        """
        super().__init__(agent_id, user_id)
        self.max_memories = max_memories
        self._memories: List[str] = []  # Just store strings with timestamp
    
    def add_memory(self, content: str) -> str:
        """
        Add a new memory.
        
        Args:
            content: The memory content as string
            
        Returns:
            The formatted memory string with timestamp
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_memory = f"[{timestamp}] {content}"
        self._memories.append(formatted_memory)
        self._update_timestamp()
        
        # Trim if necessary
        if len(self._memories) > self.max_memories:
            self._memories = self._memories[-self.max_memories:]
        
        return formatted_memory
    
    def get_memories(self, limit: Optional[int] = None) -> List[str]:
        """
        Get memories, most recent first.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of memory strings
        """
        memories = list(reversed(self._memories))  # Most recent first
        if limit:
            memories = memories[:limit]
        return memories
    
    def get_recent_memories(self, limit: int = 10) -> List[str]:
        """Get the most recent memories."""
        return self.get_memories(limit=limit)
    
    def search_memories(self, query: str, case_sensitive: bool = False) -> List[str]:
        """
        Search memories by content.
        
        Args:
            query: Search query string
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of matching memory strings
        """
        if not case_sensitive:
            query = query.lower()
        
        results = []
        for memory in reversed(self._memories):  # Most recent first
            content = memory if case_sensitive else memory.lower()
            if query in content:
                results.append(memory)
        
        return results
    
    def get_memories_count(self) -> int:
        """Get total number of memories."""
        return len(self._memories)
    
    def clear(self) -> None:
        """Clear all memories."""
        self._memories.clear()
        self._update_timestamp()
    
    def get_size(self) -> int:
        """Get number of memories."""
        return len(self._memories)
    
    def __str__(self) -> str:
        memory_type = "user" if self.is_user_profile else "agent"
        return f"EventMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={memory_type}, memories={len(self._memories)})"


class UserMemory:
    """
    Container for user-specific memories (profile + events).
    """
    
    def __init__(self, agent_id: str, user_id: str):
        """
        Initialize UserMemory.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user
        """
        self.agent_id = agent_id
        self.user_id = user_id
        self.profile = ProfileMemory(agent_id, user_id)
        self.events = EventMemory(agent_id, user_id)
    
    def __str__(self) -> str:
        return f"UserMemory(agent_id={self.agent_id}, user_id={self.user_id})"


class AgentMemory:
    """
    Container for agent-specific memories (profile + events).
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize AgentMemory.
        
        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self.profile = ProfileMemory(agent_id, "0")  # Agent uses "0" as user_id
        self.events = EventMemory(agent_id, "0")
    
    def __str__(self) -> str:
        return f"AgentMemory(agent_id={self.agent_id})"


class Memory:
    """
    Main memory container that manages both user and agent memories with database persistence.
    Automatically loads from and saves to SQLite database.
    """
    
    def __init__(self, agent_id: str, db_path: Union[str, Path] = "personalab_memory.db", auto_save: bool = True):
        """
        Initialize Memory for a specific agent with database persistence.
        
        Args:
            agent_id: Unique identifier for the agent
            db_path: Path to SQLite database file
            auto_save: Whether to automatically save changes to database
        """
        self.agent_id = agent_id
        self.db_path = Path(db_path)
        self.auto_save = auto_save
        
        # Initialize database
        self._init_database()
        
        # Load existing data or create new
        if self._load_from_database():
            # Data loaded from database
            pass
        else:
            # Create new memory
            self.agent_memory = AgentMemory(agent_id)
            self._user_memories: Dict[str, UserMemory] = {}
            if auto_save:
                self._save_to_database()
    
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
            
            # Events table - stores all events as newline-separated string
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    events_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (agent_id, user_id),
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                )
            """)
            
            conn.commit()
    
    def _load_from_database(self) -> bool:
        """
        Load memory data from database.
        
        Returns:
            True if data was loaded, False if agent not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if agent exists
            cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (self.agent_id,))
            agent_row = cursor.fetchone()
            if not agent_row:
                return False
            
            # Create agent memory
            self.agent_memory = AgentMemory(self.agent_id)
            self._user_memories: Dict[str, UserMemory] = {}
            
            # Load agent memory
            self._load_agent_memory(cursor)
            
            # Load user memories
            cursor.execute("SELECT user_id FROM users WHERE agent_id = ?", (self.agent_id,))
            user_rows = cursor.fetchall()
            
            for (user_id,) in user_rows:
                user_memory = UserMemory(self.agent_id, user_id)
                self._load_user_memory(cursor, user_memory)
                self._user_memories[user_id] = user_memory
            
            return True
    
    def _load_agent_memory(self, cursor: sqlite3.Cursor) -> None:
        """Load agent memory from database."""
        agent_id = self.agent_id
        user_id = "0"
        
        # Load agent profile
        cursor.execute("SELECT profile_data FROM profiles WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        profile_row = cursor.fetchone()
        if profile_row:
            self.agent_memory.profile.set_profile(profile_row[0])
        
        # Load agent events - split newline-separated string
        cursor.execute("SELECT events_data FROM events WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        events_row = cursor.fetchone()
        
        if events_row and events_row[0].strip():
            # Split by newlines and restore internal newlines
            events_list = [event.strip().replace('\\n', '\n') for event in events_row[0].split('\n') if event.strip()]
            self.agent_memory.events._memories = events_list
        else:
            self.agent_memory.events._memories = []
    
    def _load_user_memory(self, cursor: sqlite3.Cursor, user_memory: UserMemory) -> None:
        """Load user memory from database."""
        agent_id = user_memory.agent_id
        user_id = user_memory.user_id
        
        # Load user profile
        cursor.execute("SELECT profile_data FROM profiles WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        profile_row = cursor.fetchone()
        if profile_row:
            user_memory.profile.set_profile(profile_row[0])
        
        # Load user events - split newline-separated string
        cursor.execute("SELECT events_data FROM events WHERE agent_id = ? AND user_id = ?", (agent_id, user_id))
        events_row = cursor.fetchone()
        
        if events_row and events_row[0].strip():
            # Split by newlines and restore internal newlines
            events_list = [event.strip().replace('\\n', '\n') for event in events_row[0].split('\n') if event.strip()]
            user_memory.events._memories = events_list
        else:
            user_memory.events._memories = []
    
    def _save_to_database(self) -> None:
        """Save memory data to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Save agent
            cursor.execute("""
                INSERT OR REPLACE INTO agents (agent_id, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (self.agent_id, current_time, current_time))
            
            # Save agent memory
            self._save_agent_memory(cursor, current_time)
            
            # Save user memories
            for user_id, user_memory in self._user_memories.items():
                self._save_user_memory(cursor, user_memory, current_time)
            
            conn.commit()
    
    def _save_agent_memory(self, cursor: sqlite3.Cursor, current_time: str) -> None:
        """Save agent memory to database."""
        agent_id = self.agent_id
        user_id = "0"  # Agent uses "0" as user_id
        
        # Save agent profile
        cursor.execute("""
            INSERT OR REPLACE INTO profiles (agent_id, user_id, profile_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, user_id, self.agent_memory.profile.get_profile(), current_time, current_time))
        
        # Save agent events - merge list into newline-separated string
        # Replace internal newlines with placeholder to avoid split issues
        safe_events = [event.replace('\n', '\\n') for event in self.agent_memory.events._memories]
        events_string = '\n'.join(safe_events)
        cursor.execute("""
            INSERT OR REPLACE INTO events (agent_id, user_id, events_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, user_id, events_string, current_time, current_time))
    
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
        
        # Save user events - merge list into newline-separated string
        # Replace internal newlines with placeholder to avoid split issues
        safe_events = [event.replace('\n', '\\n') for event in user_memory.events._memories]
        events_string = '\n'.join(safe_events)
        cursor.execute("""
            INSERT OR REPLACE INTO events (agent_id, user_id, events_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, user_id, events_string, current_time, current_time))
    
    def get_user_memory(self, user_id: str) -> 'DatabaseUserMemory':
        """
        Get or create user memory for a specific user with auto-save.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            DatabaseUserMemory instance for the user
        """
        if user_id not in self._user_memories:
            self._user_memories[user_id] = UserMemory(self.agent_id, user_id)
            if self.auto_save:
                self._save_to_database()
        return DatabaseUserMemory(self._user_memories[user_id], self)
    
    def get_agent_memory(self) -> 'DatabaseAgentMemory':
        """Get agent memory with auto-save."""
        return DatabaseAgentMemory(self.agent_memory, self)
    
    def list_users(self) -> List[str]:
        """Get list of all user IDs with memories."""
        return list(self._user_memories.keys())
    
    def save(self) -> None:
        """Manually save memory to database."""
        self._save_to_database()
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get comprehensive memory information."""
        return {
            "agent_id": self.agent_id,
            "total_users": len(self._user_memories),
            "users": list(self._user_memories.keys()),
            "agent_profile_size": self.agent_memory.profile.get_size(),
            "agent_events_count": self.agent_memory.events.get_size(),
            "database_file": str(self.db_path),
            "auto_save": self.auto_save
        }
    
    def __str__(self) -> str:
        return f"Memory(agent_id={self.agent_id}, users={len(self._user_memories)}, db={self.db_path.name})"


class DatabaseUserMemory:
    """UserMemory wrapper with database auto-save functionality."""
    
    def __init__(self, user_memory: UserMemory, memory: Memory):
        self._user_memory = user_memory
        self._memory = memory
        self.agent_id = user_memory.agent_id
        self.user_id = user_memory.user_id
    
    @property
    def profile(self) -> 'DatabaseProfileMemory':
        """Get profile with auto-save."""
        return DatabaseProfileMemory(self._user_memory.profile, self._memory)
    
    @property
    def events(self) -> 'DatabaseEventMemory':
        """Get events with auto-save."""
        return DatabaseEventMemory(self._user_memory.events, self._memory)
    
    def __str__(self) -> str:
        return str(self._user_memory)


class DatabaseAgentMemory:
    """AgentMemory wrapper with database auto-save functionality."""
    
    def __init__(self, agent_memory: AgentMemory, memory: Memory):
        self._agent_memory = agent_memory
        self._memory = memory
        self.agent_id = agent_memory.agent_id
    
    @property
    def profile(self) -> 'DatabaseProfileMemory':
        """Get profile with auto-save."""
        return DatabaseProfileMemory(self._agent_memory.profile, self._memory)
    
    @property
    def events(self) -> 'DatabaseEventMemory':
        """Get events with auto-save."""
        return DatabaseEventMemory(self._agent_memory.events, self._memory)
    
    def __str__(self) -> str:
        return str(self._agent_memory)


class DatabaseProfileMemory:
    """ProfileMemory wrapper with database auto-save functionality."""
    
    def __init__(self, profile_memory: ProfileMemory, memory: Memory):
        self._profile_memory = profile_memory
        self._memory = memory
    
    def get_profile(self) -> str:
        """Get profile data."""
        return self._profile_memory.get_profile()
    
    def set_profile(self, profile_data: str) -> None:
        """Set profile data and auto-save."""
        self._profile_memory.set_profile(profile_data)
        if self._memory.auto_save:
            self._memory._save_to_database()
    
    def clear(self) -> None:
        """Clear profile and auto-save."""
        self._profile_memory.clear()
        if self._memory.auto_save:
            self._memory._save_to_database()
    
    def get_size(self) -> int:
        """Get profile size."""
        return self._profile_memory.get_size()
    
    def __str__(self) -> str:
        return str(self._profile_memory)


class DatabaseEventMemory:
    """EventMemory wrapper with database auto-save functionality."""
    
    def __init__(self, event_memory: EventMemory, memory: Memory):
        self._event_memory = event_memory
        self._memory = memory
    
    def add_memory(self, content: str) -> str:
        """Add memory and auto-save."""
        result = self._event_memory.add_memory(content)
        if self._memory.auto_save:
            self._memory._save_to_database()
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
        if self._memory.auto_save:
            self._memory._save_to_database()
    
    def get_size(self) -> int:
        """Get memory size."""
        return self._event_memory.get_size()
    
    def __str__(self) -> str:
        return str(self._event_memory) 