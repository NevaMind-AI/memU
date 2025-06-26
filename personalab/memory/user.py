"""
User memory management for PersonaLab.

This module handles user-specific memory containers that combine profile and event storage.
"""

from .profile import ProfileMemory
from .events import EventMemory


class UserMemory:
    """
    Container for user-specific memories (profile + events).
    
    This class combines profile and event memory for a specific user,
    providing a unified interface for user-related memory operations.
    """
    
    def __init__(self, agent_id: str, user_id: str):
        """
        Initialize UserMemory for a specific user.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user
        """
        self.agent_id = agent_id
        self.user_id = user_id
        self.profile = ProfileMemory(agent_id, user_id)
        self.events = EventMemory(agent_id, user_id)
    
    def clear_all(self) -> None:
        """Clear both profile and event memories."""
        self.profile.clear()
        self.events.clear()
    
    def get_total_size(self) -> int:
        """Get total size of profile and events combined."""
        return self.profile.get_size() + self.events.get_size()
    
    def is_empty(self) -> bool:
        """Check if both profile and events are empty."""
        return self.profile.is_empty() and self.events.is_empty()
    
    def get_memory_summary(self) -> dict:
        """Get a summary of user memory contents."""
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "profile": {
                "size": self.profile.get_size(),
                "empty": self.profile.is_empty(),
                "updated_at": self.profile.updated_at
            },
            "events": {
                "count": self.events.get_size(),
                "empty": self.events.is_empty(),
                "updated_at": self.events.updated_at
            },
            "total_size": self.get_total_size()
        }
    
    def search_all(self, query: str, case_sensitive: bool = False) -> dict:
        """
        Search through both profile and events.
        
        Args:
            query: Search query string
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            Dictionary with search results from profile and events
        """
        results = {
            "query": query,
            "profile_match": False,
            "profile_content": "",
            "event_matches": []
        }
        
        # Search profile
        profile_content = self.profile.get_profile()
        if profile_content:
            search_content = profile_content if case_sensitive else profile_content.lower()
            search_query = query if case_sensitive else query.lower()
            if search_query in search_content:
                results["profile_match"] = True
                results["profile_content"] = profile_content
        
        # Search events
        results["event_matches"] = self.events.search_memories(query, case_sensitive)
        
        return results
    
    def __str__(self) -> str:
        return f"UserMemory(agent_id={self.agent_id}, user_id={self.user_id}, profile_size={self.profile.get_size()}, events_count={self.events.get_size()})"
    
    def __repr__(self) -> str:
        return f"<UserMemory: {self.agent_id}/{self.user_id}, {self.get_total_size()} total size>" 