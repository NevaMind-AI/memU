"""
Memory management module for PersonaLab.

This module provides simplified string-based memory management for AI personas.
Memory is a container that manages both user and agent memories.
"""

import json
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
    Main memory container that manages both user and agent memories.
    This is the primary interface for memory management.
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize Memory for a specific agent.
        
        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self.agent_memory = AgentMemory(agent_id)
        self._user_memories: Dict[str, UserMemory] = {}
    
    def get_user_memory(self, user_id: str) -> UserMemory:
        """
        Get or create user memory for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            UserMemory instance for the user
        """
        if user_id not in self._user_memories:
            self._user_memories[user_id] = UserMemory(self.agent_id, user_id)
        return self._user_memories[user_id]
    
    def get_agent_memory(self) -> AgentMemory:
        """Get agent memory."""
        return self.agent_memory
    
    def list_users(self) -> List[str]:
        """Get list of all user IDs with memories."""
        return list(self._user_memories.keys())
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get comprehensive memory information."""
        return {
            "agent_id": self.agent_id,
            "total_users": len(self._user_memories),
            "users": list(self._user_memories.keys()),
            "agent_profile_size": self.agent_memory.profile.get_size(),
            "agent_events_count": self.agent_memory.events.get_size(),
        }
    
    def __str__(self) -> str:
        return f"Memory(agent_id={self.agent_id}, users={len(self._user_memories)})" 