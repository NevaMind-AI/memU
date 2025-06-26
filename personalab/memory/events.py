"""
Event memory management for PersonaLab.

This module handles event-based memory storage with automatic timestamping.
"""

from datetime import datetime
from typing import List, Optional

from .base import BaseMemory


class EventMemory(BaseMemory):
    """
    Manages simple string-based memories with datetime strings.
    
    This class provides event-based memory storage where each memory entry
    is automatically timestamped. No categories, no complex filtering - 
    just content and time.
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
        """
        Get the most recent memories.
        
        Args:
            limit: Number of recent memories to return
            
        Returns:
            List of recent memory strings
        """
        return self.get_memories(limit=limit)
    
    def get_all_memories(self) -> List[str]:
        """
        Get all memories in chronological order (oldest first).
        
        Returns:
            List of all memory strings in chronological order
        """
        return self._memories.copy()
    
    def search_memories(self, query: str, case_sensitive: bool = False) -> List[str]:
        """
        Search memories by content.
        
        Args:
            query: Search query string
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of matching memory strings (most recent first)
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
    
    def is_empty(self) -> bool:
        """Check if memory is empty."""
        return len(self._memories) == 0
    
    def get_memory_range(self, start_index: int = 0, end_index: Optional[int] = None) -> List[str]:
        """
        Get a range of memories by index.
        
        Args:
            start_index: Starting index (0-based)
            end_index: Ending index (exclusive). If None, goes to end
            
        Returns:
            List of memory strings in the specified range
        """
        if end_index is None:
            return self._memories[start_index:]
        return self._memories[start_index:end_index]
