"""
Memory base classes for PersonaLab.

This module implements the new unified Memory architecture as described in STRUCTURE.md:
- Memory: Unified memory class containing ProfileMemory, EventMemory, and MindMemory components
- ProfileMemory: Component for storing user/agent profile information
- EventMemory: Component for storing event-based memories
- MindMemory: Component for storing psychological insights and mind analysis
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class Memory:
    """
    Complete memory system for AI agents, integrating profile memory, event memory,
    and mind psychological analysis components.

    According to the unified memory architecture design, Memory is the central memory
    management class that internally contains:
    - ProfileMemory component: Manages profile/persona memory
    - EventMemory component: Manages event-based memories
    - MindMemory component: Manages psychological analysis and mind insights
    """

    def __init__(self, agent_id: str, user_id: str, memory_id: Optional[str] = None):
        """
        Initialize Memory object.

        Args:
            agent_id: Associated Agent ID
            user_id: Associated User ID
            memory_id: Memory ID, auto-generated if not provided
        """
        self.memory_id = memory_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Initialize memory components
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        self.mind_memory = MindMemory()

    def get_profile_content(self) -> str:
        """Get profile memory content"""
        return self.profile_memory.get_content()

    def get_event_content(self) -> List[str]:
        """Get event memory content"""
        return self.event_memory.get_content()

    def get_mind_content(self) -> List[str]:
        """Get mind memory content"""
        return self.mind_memory.get_content()

    def update_profile(self, new_profile_info: str):
        """Update profile memory"""
        self.profile_memory.set_content(new_profile_info)
        self.updated_at = datetime.now()

    def update_events(self, new_events: List[str]):
        """Update event memory"""
        current_events = self.event_memory.get_content()
        current_events.extend(new_events)
        # Keep only the most recent events (within max_events limit)
        if len(current_events) > self.event_memory.max_events:
            current_events = current_events[-self.event_memory.max_events :]
        self.event_memory.set_content(current_events)
        self.updated_at = datetime.now()

    def update_mind(self, new_insights: List[str]):
        """Update mind memory"""
        current_insights = self.mind_memory.get_content()
        current_insights.extend(new_insights)
        self.mind_memory.set_content(current_insights)
        self.updated_at = datetime.now()

    def to_prompt(self) -> str:
        """Convert complete memory to prompt format"""
        prompt = ""

        # Add profile memory
        profile_content = self.profile_memory.get_content()
        if profile_content:
            prompt += "## User Profile\n"
            prompt += f"{profile_content}\n\n"

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
                "content_type": "paragraph",
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

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get Memory summary information"""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "profile_length": len(self.get_profile_content()),
            "event_count": len(self.get_event_content()),
            "mind_count": len(self.get_mind_content()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def clear_profile(self):
        """Clear profile memory"""
        self.profile_memory = ProfileMemory()
        self.updated_at = datetime.now()

    def clear_events(self):
        """Clear event memory"""
        self.event_memory = EventMemory()
        self.updated_at = datetime.now()

    def clear_mind(self):
        """Clear mind memory"""
        self.mind_memory = MindMemory()
        self.updated_at = datetime.now()

    def clear_all(self):
        """Clear all memories"""
        self.profile_memory = ProfileMemory()
        self.event_memory = EventMemory()
        self.mind_memory = MindMemory()
        self.updated_at = datetime.now()

    # Convenient methods for different memory types
    def add_profile(self, profile_info: str):
        """Add profile information"""
        current_profile = self.get_profile_content()
        if current_profile:
            updated_profile = f"{current_profile}\n{profile_info}"
        else:
            updated_profile = profile_info
        self.update_profile(updated_profile)

    def get_profile(self) -> str:
        """Get profile information as a single text"""
        return self.get_profile_content()

    def add_events(self, events: List[str]):
        """Add events to event memory"""
        self.update_events(events)

    def get_events(self) -> List[str]:
        """Get events from event memory"""
        return self.get_event_content()

    def add_mind(self, insights: List[str]):
        """Add mind/psychological insights"""
        self.update_mind(insights)

    def get_mind(self) -> List[str]:
        """Get mind/psychological insights"""
        return self.get_mind_content()

    def close(self):
        """Close memory resources (for compatibility)"""
        # Memory doesn't have persistent connections to close
        pass

    # Backward compatibility properties
    @property
    def mind_metadata(self) -> Optional[Dict[str, Any]]:
        """Backward compatibility: Convert mind_memory to metadata format"""
        mind_content = self.mind_memory.get_content()
        if mind_content:
            return {
                "insights": "\n".join(mind_content),
                "insight_count": len(mind_content),
                "content_type": "list_of_paragraphs",
            }
        return None

    @mind_metadata.setter
    def mind_metadata(self, value: Optional[Dict[str, Any]]):
        """Backward compatibility: Set mind_memory from metadata format"""
        if value is None:
            self.mind_memory = MindMemory()
        else:
            insights_text = value.get("insights", "")
            if insights_text:
                # If it's a string, split by lines
                if isinstance(insights_text, str):
                    insights = [
                        line.strip()
                        for line in insights_text.split("\n")
                        if line.strip()
                    ]
                else:
                    insights = [str(insights_text)]

                self.mind_memory = MindMemory(insights)


class ProfileMemory:
    """
    Profile memory component.

    Internal component of the Memory class for storing user or agent profile information.
    Storage format: Single paragraph form
    """

    def __init__(self, content: str = ""):
        """
        Initialize ProfileMemory.

        Args:
            content: Initial profile content
        """
        self.content = content

    def get_content(self) -> str:
        """Get profile content"""
        return self.content

    def set_content(self, content: str):
        """
        Directly set profile content.

        Args:
            content: New profile content
        """
        self.content = content

    def is_empty(self) -> bool:
        """Check if profile memory is empty"""
        return not self.content.strip()

    def get_word_count(self) -> int:
        """Get word count of profile content"""
        return len(self.content.split())


class EventMemory:
    """
    Event memory component.

    Internal component of the Memory class for storing important events and conversation highlights.
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

    Internal component of the Memory class for storing psychological insights and mind analysis.
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

    def get_recent_insights(self, count: int = 10) -> List[str]:
        """
        Get recent insights

        Args:
            count: Number of insights to get

        Returns:
            List of recent insights
        """
        return self.insights[-count:] if count > 0 else []

    def clear_insights(self):
        """Clear all insights"""
        self.insights = []

    def to_prompt(self) -> str:
        """Convert insights to prompt format"""
        if not self.insights:
            return ""
        return "\n".join(f"- {insight}" for insight in self.insights)

    def is_empty(self) -> bool:
        """Check if mind memory is empty"""
        return len(self.insights) == 0

    def get_insight_count(self) -> int:
        """Get insight count"""
        return len(self.insights)

    def get_total_text_length(self) -> int:
        """Get total text length of all insights"""
        return sum(len(insight) for insight in self.insights)
