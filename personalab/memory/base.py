"""
Memory base classes for PersonaLab.

This module implements memory component classes:
- Memory: Unified API-based memory management class
- ProfileMemory: Component for storing user/agent profile information
- EventMemory: Component for storing event-based memories
- MindMemory: Component for storing psychological insights and mind analysis

The main Memory class is now API-based and located in manager.py
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

# Avoid circular imports
if TYPE_CHECKING:
    from .manager import MemoryClient




class Memory:
    """
    API-based Memory object that provides unified memory interface.
    
    All data is fetched from and synced with remote API endpoints.
    Uses ProfileMemory, EventMemory, and MindMemory components for code organization.
    Provides consistent interface regardless of backend implementation.
    """
    
    def __init__(self, agent_id: str, user_id: str, memory_client: Optional["MemoryClient"] = None, data: Optional[dict] = None, memory_id: Optional[str] = None):
        """
        Initialize Memory.
        
        Args:
            agent_id: Agent ID
            user_id: User ID
            memory_client: MemoryClient instance
            data: Optional memory data from API
            memory_id: Memory ID, auto-generated if not provided
        """
        self.memory_id = memory_id or data.get("memory_id", str(uuid.uuid4())) if data else str(uuid.uuid4())
        self.agent_id = agent_id
        self.user_id = user_id
        self.memory_client = memory_client
        self._data = data or {}
        
        # Set timestamps
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        if data:
            if "created_at" in data:
                try:
                    self.created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
                except:
                    pass
            if "updated_at" in data:
                try:
                    self.updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
                except:
                    pass

        # Initialize memory components based on API data
        self._init_memory_components()

    def _init_memory_components(self):
        """Initialize memory components from API data"""
        # Profile memory
        profile_content = self._data.get("profile_content", "")
        if isinstance(profile_content, list) and profile_content:
            profile_content = profile_content[0]
        self.profile_memory = ProfileMemory(content=str(profile_content) if profile_content else "")

        # Event memory
        event_content = self._data.get("event_content", [])
        if isinstance(event_content, str):
            event_content = [event_content] if event_content else []
        self.event_memory = EventMemory(events=event_content if isinstance(event_content, list) else [])

        # Mind memory
        mind_content = self._data.get("mind_content", [])
        if isinstance(mind_content, str):
            mind_content = [mind_content] if mind_content else []
        self.mind_memory = MindMemory(insights=mind_content if isinstance(mind_content, list) else [])

    def get_profile(self) -> List[str]:
        """Get profile memory content as list"""
        return self.profile_memory.get_content()

    def get_events(self) -> List[str]:
        """Get event memory content"""
        return self.event_memory.get_content()

    def get_mind(self) -> List[str]:
        """Get mind memory content"""
        return self.mind_memory.get_content()

    def get_profile_content(self) -> List[str]:
        """Get profile content as list"""
        return self.profile_memory.get_content()

    def get_profile_content_string(self) -> str:
        """Get profile content as string for backward compatibility"""
        return self.profile_memory.get_content_string()

    def get_event_content(self) -> List[str]:
        """Get event content as list"""
        return self.event_memory.get_content()

    def get_mind_content(self) -> List[str]:
        """Get mind content as list"""
        return self.mind_memory.get_content()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get Memory summary information"""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "profile_count": len(self.get_profile_content()),
            "event_count": len(self.get_event_content()),
            "mind_count": len(self.get_mind_content()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_prompt(self) -> str:
        """Get formatted memory content for LLM prompts"""
        prompt = ""

        # Add profile memory
        profile_content = self.profile_memory.get_content()
        if profile_content:
            prompt += "## User Profile\n"
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

        # Add mind memory
        mind_content = self.mind_memory.get_content()
        if mind_content:
            prompt += "## Insights\n"
            for insight in mind_content:
                prompt += f"- {insight}\n"
            prompt += "\n"

        return prompt

    def get_memory_content(self) -> str:
        """Get complete memory content (for LLM processing)"""
        return self.to_prompt()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
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
            "mind_memory": {
                "content": self.mind_memory.get_content(),
                "content_type": "list_of_paragraphs",
            },
        }

    def close(self):
        """Close memory (no-op for API mode)"""
        pass

    # Unified interface methods that delegate to API
    def update_events(self, events: List[str]) -> bool:
        """Update events via API"""
        if self.memory_client:
            return self.memory_client.update_events(self.agent_id, self.user_id, events)
        else:
            # Update local memory component if no API client
            self.event_memory.set_content(events)
            return True

    def update_profile(self, profile_info: Union[str, List[str]]) -> bool:
        """Update profile via API"""
        if self.memory_client:
            if isinstance(profile_info, list):
                # Convert list to string for API compatibility
                profile_string = "\n".join(profile_info)
            else:
                profile_string = profile_info
            return self.memory_client.update_profile(self.agent_id, self.user_id, profile_string)
        else:
            # Update local memory component if no API client
            if isinstance(profile_info, list):
                self.profile_memory.set_content(profile_info)
            else:
                self.profile_memory.set_content([profile_info] if profile_info else [])
            return True

    def update_mind(self, insights: List[str]) -> bool:
        """
        Update mind insights via API.
        
        Args:
            insights: List of mind insights
            
        Returns:
            bool: Whether update was successful
        """
        try:
            # Implementation for mind updates via API
            # This would require a corresponding API endpoint on the server
            from ..utils import get_logger
            logger = get_logger(__name__)
            
            # For now, update the local mind component
            if hasattr(self, 'mind_memory'):
                self.mind_memory.set_content(insights)
                logger.info(f"Updated mind with {len(insights)} insights")
                return True
            else:
                logger.warning("Mind memory component not available")
                return False
        except Exception as e:
            from ..utils import get_logger
            logger = get_logger(__name__)
            logger.error(f"Error updating mind: {e}")
            return False

    def clear_profile(self) -> bool:
        """Clear profile memory via API"""
        return self.update_profile("")

    def clear_events(self) -> bool:
        """Clear event memory via API"""
        return self.update_events([])

    def clear_mind(self) -> bool:
        """Clear mind memory via API"""
        return self.update_mind([])

    def clear_all(self) -> bool:
        """Clear all memories via API"""
        profile_success = self.clear_profile()
        events_success = self.clear_events()
        mind_success = self.clear_mind()
        return profile_success and events_success and mind_success



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
            content: Initial profile content as list or single string
            max_items: Maximum number of profile items
        """
        if isinstance(content, str):
            # Convert string to list for backward compatibility
            if content.strip():
                self.items = [item.strip() for item in content.split('\n') if item.strip()]
            else:
                self.items = []
        else:
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
        """Get profile content as formatted string for backward compatibility"""
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


class MindMemory:
    """
    Mind memory component.

    Component for storing psychological insights and mind analysis.
    Storage format: List of paragraphs form
    """

    def __init__(self, insights: Optional[List[str]] = None):
        """
        Initialize MindMemory.

        Args:
            insights: Initial insights list
        """
        self.insights = insights or []

    def get_content(self) -> List[str]:
        """Get insights list"""
        return self.insights.copy()

    def set_content(self, insights: List[str]):
        """Set insights list"""
        self.insights = insights


    def to_prompt(self) -> str:
        """Convert insights to prompt format"""
        if not self.insights:
            return ""
        return "\n".join(f"- {insight}" for insight in self.insights)

    def is_empty(self) -> bool:
        """Check if mind memory is empty"""
        return len(self.insights) == 0


    def get_total_text_length(self) -> int:
        """Get total text length of all insights"""
        return sum(len(insight) for insight in self.insights)

