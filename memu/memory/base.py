"""
Memory base classes for MemU.

Enhanced memory management with multiple file types:
- Memory: Comprehensive memory management class
- ProfileMemory: Component for storing user/agent profile information
- EventMemory: Component for storing event-based memories
- ReminderMemory: Component for storing reminders and todo items
- ImportantEventMemory: Component for storing significant life events
- InterestsMemory: Component for storing hobbies and interests
- StudyMemory: Component for storing learning-related information

The main Memory class uses file-based storage for all character memory types.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils import get_logger
from .file_manager import MemoryFileManager

logger = get_logger(__name__)


class Memory:
    """
    Comprehensive Memory object for character memory management.
    
    Stores and retrieves character information from multiple .md files:
    - profile.md: Character profile information
    - event.md: Character event records
    - reminder.md: Important reminders and todo items
    - important_event.md: Significant life events and milestones
    - interests.md: Hobbies, interests, and preferences
    - study.md: Learning goals, courses, and educational content
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
        """Initialize all memory components from file data"""
        # Load profile from file
        profile_content = self.file_manager.read_profile(self.character_name)
        profile_items = [line.strip() for line in profile_content.split('\n') if line.strip()] if profile_content else []
        self.profile_memory = ProfileMemory(content=profile_items)

        # Load events from file
        events_content = self.file_manager.read_events(self.character_name)
        event_lines = [line.strip() for line in events_content.split('\n') if line.strip()] if events_content else []
        self.event_memory = EventMemory(events=event_lines)

        # Load reminders from file
        reminders_content = self.file_manager.read_reminders(self.character_name)
        reminder_lines = [line.strip() for line in reminders_content.split('\n') if line.strip()] if reminders_content else []
        self.reminder_memory = ReminderMemory(reminders=reminder_lines)

        # Load important events from file
        important_events_content = self.file_manager.read_important_events(self.character_name)
        important_event_lines = [line.strip() for line in important_events_content.split('\n') if line.strip()] if important_events_content else []
        self.important_event_memory = ImportantEventMemory(events=important_event_lines)

        # Load interests from file
        interests_content = self.file_manager.read_interests(self.character_name)
        interest_lines = [line.strip() for line in interests_content.split('\n') if line.strip()] if interests_content else []
        self.interests_memory = InterestsMemory(interests=interest_lines)

        # Load study information from file
        study_content = self.file_manager.read_study(self.character_name)
        study_lines = [line.strip() for line in study_content.split('\n') if line.strip()] if study_content else []
        self.study_memory = StudyMemory(study_info=study_lines)

    # Profile memory methods
    def get_profile(self) -> List[str]:
        """Get profile memory content as list"""
        return self.profile_memory.get_content()

    def get_profile_content(self) -> List[str]:
        """Get profile content as list"""
        return self.profile_memory.get_content()

    def get_profile_content_string(self) -> str:
        """Get profile content as string"""
        return self.profile_memory.get_content_string()

    # Event memory methods
    def get_events(self) -> List[str]:
        """Get event memory content"""
        return self.event_memory.get_content()

    def get_event_content(self) -> List[str]:
        """Get event content as list"""
        return self.event_memory.get_content()

    # Reminder memory methods
    def get_reminders(self) -> List[str]:
        """Get reminder memory content"""
        return self.reminder_memory.get_content()

    def get_reminder_content(self) -> List[str]:
        """Get reminder content as list"""
        return self.reminder_memory.get_content()

    # Important event memory methods
    def get_important_events(self) -> List[str]:
        """Get important event memory content"""
        return self.important_event_memory.get_content()

    def get_important_event_content(self) -> List[str]:
        """Get important event content as list"""
        return self.important_event_memory.get_content()

    # Interests memory methods
    def get_interests(self) -> List[str]:
        """Get interests memory content"""
        return self.interests_memory.get_content()

    def get_interests_content(self) -> List[str]:
        """Get interests content as list"""
        return self.interests_memory.get_content()

    # Study memory methods
    def get_study(self) -> List[str]:
        """Get study memory content"""
        return self.study_memory.get_content()

    def get_study_content(self) -> List[str]:
        """Get study content as list"""
        return self.study_memory.get_content()

    # Generic memory access
    def get_memory_content_by_type(self, memory_type: str) -> List[str]:
        """Get memory content by type"""
        if memory_type == "profile":
            return self.get_profile_content()
        elif memory_type == "event":
            return self.get_event_content()
        elif memory_type == "reminder":
            return self.get_reminder_content()
        elif memory_type == "important_event":
            return self.get_important_event_content()
        elif memory_type == "interests":
            return self.get_interests_content()
        elif memory_type == "study":
            return self.get_study_content()
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

    def get_all_memory_content(self) -> Dict[str, List[str]]:
        """Get all memory content organized by type"""
        return {
            "profile": self.get_profile_content(),
            "event": self.get_event_content(),
            "reminder": self.get_reminder_content(),
            "important_event": self.get_important_event_content(),
            "interests": self.get_interests_content(),
            "study": self.get_study_content()
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get Memory summary information"""
        return {
            "memory_id": self.memory_id,
            "character_name": self.character_name,
            "memory_dir": self.memory_dir,
            "profile_count": len(self.get_profile_content()),
            "event_count": len(self.get_event_content()),
            "reminder_count": len(self.get_reminder_content()),
            "important_event_count": len(self.get_important_event_content()),
            "interests_count": len(self.get_interests_content()),
            "study_count": len(self.get_study_content()),
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

        # Add important events
        important_events = self.important_event_memory.get_content()
        if important_events:
            prompt += "## Important Life Events\n"
            for event in important_events:
                prompt += f"- {event}\n"
            prompt += "\n"

        # Add interests
        interests = self.interests_memory.get_content()
        if interests:
            prompt += "## Interests & Hobbies\n"
            for interest in interests:
                prompt += f"- {interest}\n"
            prompt += "\n"

        # Add study information
        study_info = self.study_memory.get_content()
        if study_info:
            prompt += "## Learning & Study\n"
            for study_item in study_info:
                prompt += f"- {study_item}\n"
            prompt += "\n"

        # Add reminders
        reminders = self.reminder_memory.get_content()
        if reminders:
            prompt += "## Current Reminders\n"
            for reminder in reminders:
                prompt += f"- {reminder}\n"
            prompt += "\n"

        # Add recent events
        event_content = self.event_memory.get_content()
        if event_content:
            prompt += "## Recent Events\n"
            for event in event_content[-10:]:  # Show last 10 events
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
            "reminder_memory": {
                "content": self.reminder_memory.get_content(),
                "content_type": "list_of_items",
            },
            "important_event_memory": {
                "content": self.important_event_memory.get_content(),
                "content_type": "list_of_paragraphs",
            },
            "interests_memory": {
                "content": self.interests_memory.get_content(),
                "content_type": "list_of_items",
            },
            "study_memory": {
                "content": self.study_memory.get_content(),
                "content_type": "list_of_items",
            },
        }

    def close(self):
        """Close memory (no-op for file mode)"""
        pass


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


class ReminderMemory:
    """
    Reminder memory component.

    Component for storing reminders, todo items, and scheduled tasks.
    Storage format: List of reminder items
    """

    def __init__(self, reminders: Optional[List[str]] = None, max_reminders: int = 50):
        """
        Initialize ReminderMemory.

        Args:
            reminders: Initial reminder list
            max_reminders: Maximum number of reminders
        """
        self.reminders = reminders or []
        self.max_reminders = max_reminders

    def get_content(self) -> List[str]:
        """Get reminder list"""
        return self.reminders.copy()

    def set_content(self, reminders: List[str]):
        """Set reminder list"""
        self.reminders = reminders

    def add_reminder(self, reminder: str):
        """
        Add a single reminder item.

        Args:
            reminder: Reminder item to add
        """
        if reminder.strip() and reminder not in self.reminders:
            self.reminders.append(reminder.strip())
            # Keep within max_reminders limit
            if len(self.reminders) > self.max_reminders:
                self.reminders = self.reminders[-self.max_reminders:]

    def clear_reminders(self):
        """Clear all reminders"""
        self.reminders = []

    def to_prompt(self) -> str:
        """Convert reminders to prompt format"""
        if not self.reminders:
            return ""
        return "\n".join(f"- {reminder}" for reminder in self.reminders)

    def is_empty(self) -> bool:
        """Check if reminder memory is empty"""
        return len(self.reminders) == 0

    def get_reminder_count(self) -> int:
        """Get reminder count"""
        return len(self.reminders)

    def get_total_text_length(self) -> int:
        """Get total text length of all reminders"""
        return sum(len(reminder) for reminder in self.reminders)


class ImportantEventMemory:
    """
    Important event memory component.

    Component for storing significant life events, milestones, and key moments.
    Storage format: List of detailed event descriptions
    """

    def __init__(self, events: Optional[List[str]] = None, max_events: int = 100):
        """
        Initialize ImportantEventMemory.

        Args:
            events: Initial important event list
            max_events: Maximum number of important events
        """
        self.events = events or []
        self.max_events = max_events

    def get_content(self) -> List[str]:
        """Get important event list"""
        return self.events.copy()

    def set_content(self, events: List[str]):
        """Set important event list"""
        self.events = events

    def add_event(self, event: str):
        """
        Add a single important event.

        Args:
            event: Important event to add
        """
        if event.strip() and event not in self.events:
            self.events.append(event.strip())
            # Keep within max_events limit
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]

    def get_recent_events(self, count: int = 10) -> List[str]:
        """
        Get recent important events

        Args:
            count: Number of events to get

        Returns:
            List of recent important events
        """
        return self.events[-count:] if count > 0 else []

    def clear_events(self):
        """Clear all important events"""
        self.events = []

    def to_prompt(self) -> str:
        """Convert important events to prompt format"""
        if not self.events:
            return ""
        return "\n".join(f"- {event}" for event in self.events)

    def is_empty(self) -> bool:
        """Check if important event memory is empty"""
        return len(self.events) == 0

    def get_event_count(self) -> int:
        """Get important event count"""
        return len(self.events)

    def get_total_text_length(self) -> int:
        """Get total text length of all important events"""
        return sum(len(event) for event in self.events)


class InterestsMemory:
    """
    Interests memory component.

    Component for storing hobbies, interests, preferences, and likes.
    Storage format: List of interest items
    """

    def __init__(self, interests: Optional[List[str]] = None, max_interests: int = 100):
        """
        Initialize InterestsMemory.

        Args:
            interests: Initial interests list
            max_interests: Maximum number of interests
        """
        self.interests = interests or []
        self.max_interests = max_interests

    def get_content(self) -> List[str]:
        """Get interests list"""
        return self.interests.copy()

    def set_content(self, interests: List[str]):
        """Set interests list"""
        self.interests = interests

    def add_interest(self, interest: str):
        """
        Add a single interest item.

        Args:
            interest: Interest item to add
        """
        if interest.strip() and interest not in self.interests:
            self.interests.append(interest.strip())
            # Keep within max_interests limit
            if len(self.interests) > self.max_interests:
                self.interests = self.interests[-self.max_interests:]

    def clear_interests(self):
        """Clear all interests"""
        self.interests = []

    def to_prompt(self) -> str:
        """Convert interests to prompt format"""
        if not self.interests:
            return ""
        return "\n".join(f"- {interest}" for interest in self.interests)

    def is_empty(self) -> bool:
        """Check if interests memory is empty"""
        return len(self.interests) == 0

    def get_interest_count(self) -> int:
        """Get interest count"""
        return len(self.interests)

    def get_total_text_length(self) -> int:
        """Get total text length of all interests"""
        return sum(len(interest) for interest in self.interests)


class StudyMemory:
    """
    Study memory component.

    Component for storing learning goals, courses, educational content, and study progress.
    Storage format: List of study-related items
    """

    def __init__(self, study_info: Optional[List[str]] = None, max_items: int = 100):
        """
        Initialize StudyMemory.

        Args:
            study_info: Initial study information list
            max_items: Maximum number of study items
        """
        self.study_info = study_info or []
        self.max_items = max_items

    def get_content(self) -> List[str]:
        """Get study information list"""
        return self.study_info.copy()

    def set_content(self, study_info: List[str]):
        """Set study information list"""
        self.study_info = study_info

    def add_study_item(self, item: str):
        """
        Add a single study item.

        Args:
            item: Study item to add
        """
        if item.strip() and item not in self.study_info:
            self.study_info.append(item.strip())
            # Keep within max_items limit
            if len(self.study_info) > self.max_items:
                self.study_info = self.study_info[-self.max_items:]

    def clear_study_info(self):
        """Clear all study information"""
        self.study_info = []

    def to_prompt(self) -> str:
        """Convert study information to prompt format"""
        if not self.study_info:
            return ""
        return "\n".join(f"- {item}" for item in self.study_info)

    def is_empty(self) -> bool:
        """Check if study memory is empty"""
        return len(self.study_info) == 0

    def get_study_item_count(self) -> int:
        """Get study item count"""
        return len(self.study_info)

    def get_total_text_length(self) -> int:
        """Get total text length of all study items"""
        return sum(len(item) for item in self.study_info)

