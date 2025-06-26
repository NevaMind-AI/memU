"""
Agent memory management for PersonaLab.

This module handles agent-specific memory containers that combine profile and event storage.
"""

from .profile import ProfileMemory
from .events import EventMemory


class AgentMemory:
    """
    Container for agent-specific memories (profile + events).
    
    This class combines profile and event memory for the agent itself,
    providing a unified interface for agent-related memory operations.
    Note: Agent memories use user_id="0" by convention.
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize AgentMemory for the agent.
        
        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self.user_id = "0"  # Agent always uses "0" as user_id
        self.profile = ProfileMemory(agent_id, "0")  # Agent profile
        self.events = EventMemory(agent_id, "0")     # Agent events
    
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
        """Get a summary of agent memory contents."""
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "memory_type": "agent",
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
    
    