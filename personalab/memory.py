"""
Memory management module for PersonaLab.

This module provides simplified string-based memory management for AI personas.
Memory is a container that manages both user and agent memories.
"""

import json
import sqlite3
import re
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
    
    def should_search_memory(self, conversation: str, system_prompt: str = "") -> bool:
        """
        Determine if memory search is needed based on conversation content and system prompt.
        
        Args:
            conversation: Full user-agent conversation
            system_prompt: System prompt text
            
        Returns:
            True if memory search should be performed, False otherwise
        """
        # Combine conversation and system prompt for analysis
        full_text = f"{system_prompt}\n{conversation}".lower()
        
        # Keywords that indicate memory search might be useful
        memory_keywords = [
            "remember", "recall", "previous", "before", "earlier", "last time",
            "you said", "we discussed", "mentioned", "talked about", "history",
            "past", "context", "background", "what did", "do you know about",
            "tell me about", "familiar with", "experience with", "learned",
            "saved", "stored", "recorded", "noted", "documented"
        ]
        
        # Question words that often indicate information retrieval
        question_keywords = [
            "what", "when", "where", "who", "how", "why", "which", "can you",
            "do you", "have you", "did you", "will you", "could you", "would you"
        ]
        
        # Check for memory-related keywords
        memory_score = sum(1 for keyword in memory_keywords if keyword in full_text)
        
        # Check for questions that might benefit from memory
        question_score = sum(1 for keyword in question_keywords if keyword in full_text)
        
        # Check if there are personal pronouns indicating ongoing relationship
        personal_pronouns = ["my", "me", "i", "you", "we", "us", "our"]
        personal_score = sum(1 for pronoun in personal_pronouns if pronoun in full_text)
        
        # Simple scoring system - adjust thresholds as needed
        total_score = memory_score * 3 + question_score * 1 + (personal_score > 0) * 2
        
        # Return True if score suggests memory search would be beneficial
        return total_score >= 3

    def search_memory_with_context(self, conversation: str, system_prompt: str = "", 
                                 user_id: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
        """
        Search through memories using conversation context and system prompt.
        
        Args:
            conversation: Full user-agent conversation
            system_prompt: System prompt text
            user_id: Specific user ID to search (if None, searches agent and all users)
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results with metadata
        """
        # Extract search terms from conversation and system prompt
        search_terms = self._extract_search_terms(conversation, system_prompt)
        
        search_results = {
            "search_terms": search_terms,
            "agent_profile_matches": [],
            "agent_event_matches": [],
            "user_profile_matches": [],
            "user_event_matches": [],
            "total_matches": 0
        }
        
        if not search_terms:
            return search_results
        
        # Search agent memories
        agent_profile = self.agent_memory.profile.get_profile()
        if agent_profile:
            profile_matches = self._search_text(agent_profile, search_terms)
            if profile_matches:
                search_results["agent_profile_matches"] = [{
                    "content": agent_profile,
                    "match_score": profile_matches["score"],
                    "matched_terms": profile_matches["matched_terms"]
                }]
        
        # Search agent events
        agent_events = self.agent_memory.events.get_memories()
        for event in agent_events[:max_results]:
            event_matches = self._search_text(event, search_terms)
            if event_matches:
                search_results["agent_event_matches"].append({
                    "content": event,
                    "match_score": event_matches["score"],
                    "matched_terms": event_matches["matched_terms"]
                })
        
        # Search user memories
        users_to_search = [user_id] if user_id else list(self._user_memories.keys())
        
        for uid in users_to_search:
            if uid in self._user_memories:
                user_memory = self._user_memories[uid]
                
                # Search user profile
                user_profile = user_memory.profile.get_profile()
                if user_profile:
                    profile_matches = self._search_text(user_profile, search_terms)
                    if profile_matches:
                        search_results["user_profile_matches"].append({
                            "user_id": uid,
                            "content": user_profile,
                            "match_score": profile_matches["score"],
                            "matched_terms": profile_matches["matched_terms"]
                        })
                
                # Search user events
                user_events = user_memory.events.get_memories()
                for event in user_events[:max_results]:
                    event_matches = self._search_text(event, search_terms)
                    if event_matches:
                        search_results["user_event_matches"].append({
                            "user_id": uid,
                            "content": event,
                            "match_score": event_matches["score"],
                            "matched_terms": event_matches["matched_terms"]
                        })
        
        # Sort results by match score (highest first)
        search_results["agent_event_matches"].sort(key=lambda x: x["match_score"], reverse=True)
        search_results["user_profile_matches"].sort(key=lambda x: x["match_score"], reverse=True)
        search_results["user_event_matches"].sort(key=lambda x: x["match_score"], reverse=True)
        
        # Limit results
        search_results["agent_event_matches"] = search_results["agent_event_matches"][:max_results]
        search_results["user_profile_matches"] = search_results["user_profile_matches"][:max_results]
        search_results["user_event_matches"] = search_results["user_event_matches"][:max_results]
        
        # Calculate total matches
        search_results["total_matches"] = (
            len(search_results["agent_profile_matches"]) +
            len(search_results["agent_event_matches"]) +
            len(search_results["user_profile_matches"]) +
            len(search_results["user_event_matches"])
        )
        
        return search_results

    def _extract_search_terms(self, conversation: str, system_prompt: str) -> List[str]:
        """
        Extract meaningful search terms from conversation and system prompt.
        
        Args:
            conversation: User-agent conversation
            system_prompt: System prompt
            
        Returns:
            List of search terms
        """
        # Combine text sources
        full_text = f"{system_prompt}\n{conversation}"
        
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the", "is", "at", "which", "on", "a", "an", "and", "or", "but", 
            "in", "with", "to", "for", "of", "as", "by", "that", "this",
            "be", "have", "do", "will", "would", "could", "should", "may",
            "might", "can", "must", "shall", "i", "you", "he", "she", "it",
            "we", "they", "me", "him", "her", "us", "them", "my", "your",
            "his", "her", "its", "our", "their"
        }
        
        # Extract words (including numbers and basic punctuation)
        words = re.findall(r'\b\w+\b', full_text.lower())
        
        # Filter out stop words and short words
        meaningful_words = [
            word for word in words 
            if len(word) >= 3 and word not in stop_words
        ]
        
        # Remove duplicates while preserving order
        search_terms = []
        seen = set()
        for word in meaningful_words:
            if word not in seen:
                search_terms.append(word)
                seen.add(word)
        
        # Limit to most relevant terms (latest conversation usually more important)
        return search_terms[-20:]  # Return last 20 unique terms

    def _search_text(self, text: str, search_terms: List[str]) -> Optional[Dict[str, Any]]:
        """
        Search for terms in text and return match information.
        
        Args:
            text: Text to search in
            search_terms: Terms to search for
            
        Returns:
            Dictionary with match score and matched terms, or None if no matches
        """
        if not text or not search_terms:
            return None
        
        text_lower = text.lower()
        matched_terms = []
        match_score = 0
        
        for term in search_terms:
            if term in text_lower:
                matched_terms.append(term)
                # Score based on term frequency and length
                frequency = text_lower.count(term)
                term_score = frequency * len(term)
                match_score += term_score
        
        if matched_terms:
            return {
                "score": match_score,
                "matched_terms": matched_terms,
                "match_count": len(matched_terms)
            }
        
        return None

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

    def search_memory_with_context(self, conversation: str, system_prompt: str = "", 
                                 max_results: int = 10) -> Dict[str, Any]:
        """
        Search this user's memories using conversation context.
        
        Args:
            conversation: Full user-agent conversation
            system_prompt: System prompt text
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results with metadata
        """
        return self._memory.search_memory_with_context(
            conversation, system_prompt, self.user_id, max_results
        )

    def should_search_memory(self, conversation: str, system_prompt: str = "") -> bool:
        """
        Determine if memory search is needed for this user.
        
        Args:
            conversation: Full user-agent conversation
            system_prompt: System prompt text
            
        Returns:
            True if memory search should be performed, False otherwise
        """
        return self._memory.should_search_memory(conversation, system_prompt)
    
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

    def search_memory_with_context(self, conversation: str, system_prompt: str = "", 
                                 max_results: int = 10) -> Dict[str, Any]:
        """
        Search all memories (agent and users) using conversation context.
        
        Args:
            conversation: Full user-agent conversation
            system_prompt: System prompt text
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results with metadata
        """
        return self._memory.search_memory_with_context(
            conversation, system_prompt, None, max_results
        )

    def should_search_memory(self, conversation: str, system_prompt: str = "") -> bool:
        """
        Determine if memory search is needed.
        
        Args:
            conversation: Full user-agent conversation
            system_prompt: System prompt text
            
        Returns:
            True if memory search should be performed, False otherwise
        """
        return self._memory.should_search_memory(conversation, system_prompt)
    
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