"""
Base memory class for PersonaLab.

This module defines the abstract base class that all memory implementations inherit from.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict


class BaseMemory(ABC):
    """
    Abstract base class for all memory types.
    
    This class defines the common interface and functionality that all memory types
    must implement, including timestamps, basic metadata, and abstract methods.
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
    def get_size(self) -> int:
        """Get the size/count of memory data."""
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