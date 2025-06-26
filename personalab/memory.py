"""
Memory management module for PersonaLab.

This module provides simplified string-based memory management for AI personas.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class Memory:
    """Represents a single memory entry."""
    
    def __init__(self, content: str, datetime_str: Optional[str] = None):
        """
        Initialize a memory entry.
        
        Args:
            content: The memory content as string
            datetime_str: Optional datetime string, defaults to current time
        """
        self.content = content
        self.datetime_str = datetime_str or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def to_dict(self) -> Dict[str, str]:
        """Convert memory to dictionary."""
        return {
            "content": self.content,
            "datetime_str": self.datetime_str
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Memory':
        """Create memory from dictionary."""
        return cls(data["content"], data["datetime_str"])
    
    def __str__(self) -> str:
        return f"[{self.datetime_str}] {self.content}"


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
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save memory data to JSON file."""
        pass
    
    @classmethod
    @abstractmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'BaseMemory':
        """Load memory data from JSON file."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memory data."""
        pass
    
    @abstractmethod
    def get_size(self) -> int:
        """Get the size/count of memory items."""
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
    Manages persona profile information as string-based key-value pairs.
    """
    
    def __init__(self, agent_id: str, user_id: str = "0", profile_data: Optional[Dict[str, str]] = None):
        """
        Initialize ProfileMemory.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only profiles)
            profile_data: Initial profile data dictionary (string values only)
        """
        super().__init__(agent_id, user_id)
        self._profile: Dict[str, str] = profile_data or {}
    
    def get_profile(self) -> Dict[str, str]:
        """Get complete profile data."""
        return self._profile.copy()
    
    def get_field(self, field_name: str, default: str = "") -> str:
        """Get specific field from profile."""
        return self._profile.get(field_name, default)
    
    def set_field(self, field_name: str, value: str) -> None:
        """Set specific field in profile."""
        self._profile[field_name] = str(value)
        self._update_timestamp()
    
    def update_profile(self, updates: Dict[str, str]) -> None:
        """Update multiple profile fields."""
        for key, value in updates.items():
            self._profile[key] = str(value)
        self._update_timestamp()
    
    def remove_field(self, field_name: str) -> bool:
        """Remove field from profile."""
        if field_name in self._profile:
            del self._profile[field_name]
            self._update_timestamp()
            return True
        return False
    
    def has_field(self, field_name: str) -> bool:
        """Check if field exists in profile."""
        return field_name in self._profile
    
    def clear(self) -> None:
        """Clear all profile data."""
        self._profile.clear()
        self._update_timestamp()
    
    def get_size(self) -> int:
        """Get number of profile fields."""
        return len(self._profile)
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save profile to JSON file."""
        profile_data = {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "profile": self._profile,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'ProfileMemory':
        """Load profile from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both new format and legacy format
        if "agent_id" in data and "user_id" in data:
            instance = cls(data["agent_id"], data["user_id"], data.get("profile", {}))
        else:
            # Legacy support: try to parse from old persona_id format
            persona_id = data.get("persona_id", "unknown:0")
            if ":" in persona_id:
                agent_id, user_id = persona_id.split(":", 1)
            else:
                agent_id, user_id = persona_id, "0"
            instance = cls(agent_id, user_id, data.get("profile", {}))
        
        # Set timestamps
        instance.created_at = data.get("created_at", instance.created_at)
        instance.updated_at = data.get("updated_at", instance.updated_at)
        return instance
    
    def __str__(self) -> str:
        profile_type = "user" if self.is_user_profile else "agent"
        return f"ProfileMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={profile_type}, fields={len(self._profile)})"


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
        self._memories: List[Memory] = []
    
    def add_memory(self, content: str) -> Memory:
        """
        Add a new memory.
        
        Args:
            content: The memory content as string
            
        Returns:
            The created Memory object
        """
        memory = Memory(content)
        self._memories.append(memory)
        self._update_timestamp()
        
        # Trim if necessary
        if len(self._memories) > self.max_memories:
            self._memories = self._memories[-self.max_memories:]
        
        return memory
    
    def get_memories(self, limit: Optional[int] = None) -> List[Memory]:
        """
        Get memories, most recent first.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of Memory objects
        """
        memories = list(reversed(self._memories))  # Most recent first
        if limit:
            memories = memories[:limit]
        return memories
    
    def get_recent_memories(self, limit: int = 10) -> List[Memory]:
        """Get the most recent memories."""
        return self.get_memories(limit=limit)
    
    def search_memories(self, query: str, case_sensitive: bool = False) -> List[Memory]:
        """
        Search memories by content.
        
        Args:
            query: Search query string
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of matching Memory objects
        """
        if not case_sensitive:
            query = query.lower()
        
        results = []
        for memory in reversed(self._memories):  # Most recent first
            content = memory.content if case_sensitive else memory.content.lower()
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
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save memories to JSON file."""
        memories_data = {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "max_memories": self.max_memories,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "memories": [memory.to_dict() for memory in self._memories]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memories_data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'EventMemory':
        """Load memories from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both new format and legacy format
        if "agent_id" in data and "user_id" in data:
            instance = cls(data["agent_id"], data["user_id"], data.get("max_memories", 1000))
        else:
            # Legacy support: try to parse from old persona_id format
            persona_id = data.get("persona_id", "unknown:0")
            if ":" in persona_id:
                agent_id, user_id = persona_id.split(":", 1)
            else:
                agent_id, user_id = persona_id, "0"
            instance = cls(agent_id, user_id, data.get("max_memories", 1000))
        
        # Set timestamps
        instance.created_at = data.get("created_at", instance.created_at)
        instance.updated_at = data.get("updated_at", instance.updated_at)
        
        # Load memories
        memories_data = data.get("memories", [])
        instance._memories = [Memory.from_dict(mem) for mem in memories_data]
        
        return instance
    
    def __str__(self) -> str:
        memory_type = "user" if self.is_user_profile else "agent"
        return f"EventMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={memory_type}, memories={len(self._memories)})" 