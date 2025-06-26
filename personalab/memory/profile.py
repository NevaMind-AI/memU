"""
Profile memory management for PersonaLab.

This module handles persona profile information storage and management.
"""

from .base import BaseMemory


class ProfileMemory(BaseMemory):
    """
    Manages persona profile information as a single string.
    
    This class stores and manages profile data for both agents and users,
    providing methods to get, set, and clear profile information.
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
        """
        Get complete profile data.
        
        Returns:
            The current profile data as a string
        """
        return self._profile
    
    def set_profile(self, profile_data: str) -> None:
        """
        Set profile data.
        
        Args:
            profile_data: New profile data to set
        """
        self._profile = str(profile_data)
        self._update_timestamp()
    
    def get_size(self) -> int:
        """Get length of profile string."""
        return len(self._profile)
    
    def is_empty(self) -> bool:
        """Check if profile is empty."""
        return len(self._profile.strip()) == 0
    
    def __str__(self) -> str:
        profile_type = "user" if self.is_user_profile else "agent"
        return f"ProfileMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={profile_type}, length={len(self._profile)})"
    
    def __repr__(self) -> str:
        return f"<ProfileMemory: {self.agent_id}/{self.user_id}, {len(self._profile)} chars>" 