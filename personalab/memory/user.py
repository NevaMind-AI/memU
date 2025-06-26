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

    
    def get_total_size(self) -> int:
        """Get total size of profile and events combined."""
        return self.profile.get_size() + self.events.get_size()
    
    def is_empty(self) -> bool:
        """Check if both profile and events are empty."""
        return self.profile.is_empty() and self.events.is_empty()
    