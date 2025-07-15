"""
Memory base classes for MemU.

Simplified file-based memory management:
- Memory: Simple file-based memory management class
- ProfileMemory: Component for storing user/agent profile information
- EventMemory: Component for storing event-based memories

The main Memory class now uses file-based storage for character profiles and events.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils import get_logger
from .file_manager import MemoryFileManager

logger = get_logger(__name__)


class Memory:
    """
    File-based Memory object for character memory management.
    
    Stores and retrieves character profiles and events from .md files.
    Simplified interface for direct file operations.
    """
    
    def __init__(self, character_name: str, memory_dir: str = "memory", memory_id: Optional[str] = None):
        """
        Initialize Memory.
        
        Args:
            character_name: Name of the character
            memory_dir: Directory to store memory files
            memory_id: Memory ID, auto-generated if not provided
        """
        self.memory_id = memory_id or str(uuid.uuid4())
        self.character_name = character_name
        self.memory_dir = memory_dir
        
        # Set timestamps
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Initialize file manager
        self.file_manager = MemoryFileManager(memory_dir)

        # Initialize memory components
        self._init_memory_components()

    def _init_memory_components(self):
        """Initialize memory components from file data"""
        # Load profile from file
        profile_content = self.file_manager.read_profile(self.character_name)
        profile_items = [line.strip() for line in profile_content.split('\n') if line.strip()] if profile_content else []
        self.profile_memory = ProfileMemory(content=profile_items)

        # Load events from file
        events_content = self.file_manager.read_events(self.character_name)
        event_lines = [line.strip() for line in events_content.split('\n') if line.strip()] if events_content else []
        self.event_memory = EventMemory(events=event_lines)

    def get_profile(self) -> List[str]:
        """Get profile memory content as list"""
        return self.profile_memory.get_content()

    def get_events(self) -> List[str]:
        """Get event memory content"""
        return self.event_memory.get_content()

    def get_profile_content(self) -> List[str]:
        """Get profile content as list"""
        return self.profile_memory.get_content()

    def get_profile_content_string(self) -> str:
        """Get profile content as string"""
        return self.profile_memory.get_content_string()

    def get_event_content(self) -> List[str]:
        """Get event content as list"""
        return self.event_memory.get_content()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get Memory summary information"""
        return {
            "memory_id": self.memory_id,
            "character_name": self.character_name,
            "memory_dir": self.memory_dir,
            "profile_count": len(self.get_profile_content()),
            "event_count": len(self.get_event_content()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_prompt(self) -> str:
        """Get formatted memory content for LLM prompts"""
        prompt = ""

        # Add profile memory
        profile_content = self.profile_memory.get_content()
        if profile_content:
            prompt += "## Character Profile\n"
            for profile_item in profile_content:
                prompt += f"- {profile_item}\n"
            prompt += "\n"

        # Add event memory
        event_content = self.event_memory.get_content()
        if event_content:
            prompt += "## Related Events\n"
            for event in event_content:
                prompt += f"- {event}\n"
            prompt += "\n"

        return prompt

    def get_memory_content(self) -> str:
        """Get complete memory content (for LLM processing)"""
        return self.to_prompt()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "memory_id": self.memory_id,
            "character_name": self.character_name,
            "memory_dir": self.memory_dir,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "profile_memory": {
                "content": self.profile_memory.get_content(),
                "content_type": "list_of_items",
            },
            "event_memory": {
                "content": self.event_memory.get_content(),
                "content_type": "list_of_paragraphs",
            },
        }

    def close(self):
        """Close memory (no-op for file mode)"""
        pass

    # File-based update methods
    def update_profile(self, profile_info: str) -> bool:
        """
        Update profile via file
        
        Args:
            profile_info: Profile information as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.file_manager.write_profile(self.character_name, profile_info)
            if success:
                self.updated_at = datetime.now()
                # Refresh memory components
                self._init_memory_components()
            return success
        except Exception as e:
            logger.error(f"Error updating profile for {self.character_name}: {e}")
            return False

    def update_events(self, events: List[str]) -> bool:
        """
        Update events via file
        
        Args:
            events: List of event strings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            events_content = '\n'.join(events)
            success = self.file_manager.write_events(self.character_name, events_content)
            if success:
                self.updated_at = datetime.now()
                # Refresh memory components
                self._init_memory_components()
            return success
        except Exception as e:
            logger.error(f"Error updating events for {self.character_name}: {e}")
            return False

    def append_events(self, new_events: List[str]) -> bool:
        """
        Append new events to existing events
        
        Args:
            new_events: List of new event strings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            new_events_content = '\n'.join(new_events)
            success = self.file_manager.append_events(self.character_name, new_events_content)
            if success:
                self.updated_at = datetime.now()
                # Refresh memory components
                self._init_memory_components()
            return success
        except Exception as e:
            logger.error(f"Error appending events for {self.character_name}: {e}")
            return False

    def clear_profile(self) -> bool:
        """Clear profile memory"""
        return self.update_profile("")

    def clear_events(self) -> bool:
        """Clear event memory"""
        return self.update_events([])

    def clear_all(self) -> bool:
        """Clear all memories"""
        profile_success = self.clear_profile()
        events_success = self.clear_events()
        return profile_success and events_success


class ProfileMemory:
    """
    Profile memory component.

    Component for storing user or agent profile information.
    Storage format: List of profile items
    """

    def __init__(self, content: Optional[List[str]] = None, max_items: int = 100):
        """
        Initialize ProfileMemory.

        Args:
            content: Initial profile content as list
            max_items: Maximum number of profile items
        """
        self.items = content or []
        self.max_items = max_items

    def get_content(self) -> List[str]:
        """Get profile content as list"""
        return self.items.copy()

    def set_content(self, content: List[str]):
        """
        Set profile content.

        Args:
            content: New profile content as list
        """
        self.items = content

    def add_item(self, item: str):
        """
        Add a single profile item.

        Args:
            item: Profile item to add
        """
        if item.strip() and item not in self.items:
            self.items.append(item.strip())
            # Keep within max_items limit
            if len(self.items) > self.max_items:
                self.items = self.items[-self.max_items:]

    def get_content_string(self) -> str:
        """Get profile content as formatted string"""
        return "\n".join(self.items)

    def to_prompt(self) -> str:
        """Convert profile to prompt format"""
        if not self.items:
            return ""
        return "\n".join(f"- {item}" for item in self.items)

    def is_empty(self) -> bool:
        """Check if profile memory is empty"""
        return len(self.items) == 0

    def get_total_text_length(self) -> int:
        """Get total text length of all profile items"""
        return sum(len(item) for item in self.items)


class EventMemory:
    """
    Event memory component.

    Component for storing important events and conversation highlights.
    Storage format: List of paragraphs form
    """

    def __init__(self, events: Optional[List[str]] = None, max_events: int = 50):
        """
        Initialize EventMemory.

        Args:
            events: Initial event list
            max_events: Maximum number of events
        """
        self.events = events or []
        self.max_events = max_events

    def get_content(self) -> List[str]:
        """Get event list"""
        return self.events.copy()

    def set_content(self, events: List[str]):
        """Set event list"""
        self.events = events

    def get_recent_events(self, count: int = 10) -> List[str]:
        """
        Get recent events

        Args:
            count: Number of events to get

        Returns:
            List of recent events
        """
        return self.events[-count:] if count > 0 else []

    def clear_events(self):
        """Clear all events"""
        self.events = []

    def to_prompt(self) -> str:
        """Convert events to prompt format"""
        if not self.events:
            return ""
        return "\n".join(f"- {event}" for event in self.events)

    def is_empty(self) -> bool:
        """Check if event memory is empty"""
        return len(self.events) == 0

    def get_event_count(self) -> int:
        """Get event count"""
        return len(self.events)

    def get_total_text_length(self) -> int:
        """Get total text length of all events"""
        return sum(len(event) for event in self.events)

