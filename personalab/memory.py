"""
Memory management module for PersonaLab.

This module provides classes for managing AI persona profiles and event memories.
"""

import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Event:
    """Represents a single event in memory."""
    
    timestamp: float
    event_type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    importance: int = 1  # 1-10 scale, 10 being most important
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(**data)
    
    @property
    def datetime(self) -> datetime:
        """Get datetime object from timestamp."""
        return datetime.fromtimestamp(self.timestamp)
    
    def __str__(self) -> str:
        return f"Event({self.event_type}): {self.content} [{self.datetime.strftime('%Y-%m-%d %H:%M:%S')}]"


class BaseMemory(ABC):
    """
    Abstract base class for all memory types.
    
    This class provides common functionality and interface for different memory types
    such as profile memory and event memory.
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
        self._created_at = time.time()
        self._updated_at = time.time()
    
    @property
    def created_at(self) -> datetime:
        """Get creation datetime."""
        return datetime.fromtimestamp(self._created_at)
    
    @property
    def updated_at(self) -> datetime:
        """Get last update datetime."""
        return datetime.fromtimestamp(self._updated_at)
    
    def _update_timestamp(self) -> None:
        """Update the last modification timestamp."""
        self._updated_at = time.time()
    
    @abstractmethod
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save memory data to JSON file.
        
        Args:
            file_path: Path to save the memory data
        """
        pass
    
    @classmethod
    @abstractmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'BaseMemory':
        """
        Load memory data from JSON file.
        
        Args:
            file_path: Path to load the memory data from
            
        Returns:
            Memory instance
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memory data."""
        pass
    
    @abstractmethod
    def get_size(self) -> int:
        """
        Get the size/count of memory items.
        
        Returns:
            Number of items in memory
        """
        pass
    
    @property
    def is_user_profile(self) -> bool:
        """
        Check if this is a user-specific profile.
        
        Returns:
            True if user_id is not "0", False otherwise
        """
        return self.user_id != "0"
    
    @property
    def is_agent_profile(self) -> bool:
        """
        Check if this is an agent-only profile.
        
        Returns:
            True if user_id is "0", False otherwise
        """
        return self.user_id == "0"
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get general information about this memory instance.
        
        Returns:
            Dictionary containing memory metadata
        """
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "memory_type": self.__class__.__name__,
            "is_user_profile": self.is_user_profile,
            "is_agent_profile": self.is_agent_profile,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "size": self.get_size()
        }


class ProfileMemory(BaseMemory):
    """
    Manages persona profile information including basic info, preferences, and configuration.
    
    This class handles storage and retrieval of static or semi-static persona information
    such as personality traits, preferences, background information, and configuration settings.
    """
    
    def __init__(self, agent_id: str, user_id: str = "0", profile_data: Optional[Dict[str, Any]] = None):
        """
        Initialize ProfileMemory for a specific agent and user combination.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only profiles)
            profile_data: Initial profile data dictionary
        """
        super().__init__(agent_id, user_id)
        self._profile: Dict[str, Any] = profile_data or {}
    
    def get_profile(self) -> Dict[str, Any]:
        """
        Get complete profile data.
        
        Returns:
            Dictionary containing all profile information
        """
        return self._profile.copy()
    
    def get_field(self, field_name: str, default: Any = None) -> Any:
        """
        Get specific field from profile.
        
        Args:
            field_name: Name of the field to retrieve
            default: Default value if field doesn't exist
            
        Returns:
            Field value or default
        """
        return self._profile.get(field_name, default)
    
    def set_field(self, field_name: str, value: Any) -> None:
        """
        Set specific field in profile.
        
        Args:
            field_name: Name of the field to set
            value: Value to set
        """
        self._profile[field_name] = value
        self._update_timestamp()
    
    def update_profile(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple profile fields.
        
        Args:
            updates: Dictionary of field updates
        """
        self._profile.update(updates)
        self._update_timestamp()
    
    def remove_field(self, field_name: str) -> bool:
        """
        Remove field from profile.
        
        Args:
            field_name: Name of the field to remove
            
        Returns:
            True if field was removed, False if it didn't exist
        """
        if field_name in self._profile:
            del self._profile[field_name]
            self._update_timestamp()
            return True
        return False
    
    def has_field(self, field_name: str) -> bool:
        """
        Check if profile has specific field.
        
        Args:
            field_name: Name of the field to check
            
        Returns:
            True if field exists, False otherwise
        """
        return field_name in self._profile
    
    def clear(self) -> None:
        """Clear all profile data."""
        self._profile.clear()
        self._update_timestamp()
    
    def get_size(self) -> int:
        """
        Get the number of profile fields.
        
        Returns:
            Number of fields in profile
        """
        return len(self._profile)
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save profile to JSON file.
        
        Args:
            file_path: Path to save the profile
        """
        profile_data = {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "profile": self._profile,
            "created_at": self._created_at,
            "updated_at": self._updated_at
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'ProfileMemory':
        """
        Load profile from JSON file.
        
        Args:
            file_path: Path to load the profile from
            
        Returns:
            ProfileMemory instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both old format (persona_id) and new format (agent_id, user_id)
        if "agent_id" in data and "user_id" in data:
            instance = cls(data["agent_id"], data["user_id"], data["profile"])
        else:
            # Legacy support: parse persona_id as agent_id:user_id
            persona_id = data["persona_id"]
            if ":" in persona_id:
                agent_id, user_id = persona_id.split(":", 1)
            else:
                agent_id, user_id = persona_id, "0"
            instance = cls(agent_id, user_id, data["profile"])
        
        instance._created_at = data.get("created_at", time.time())
        instance._updated_at = data.get("updated_at", time.time())
        return instance
    
    def __str__(self) -> str:
        profile_type = "user" if self.is_user_profile else "agent"
        return f"ProfileMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={profile_type}, fields={len(self._profile)})"


class EventMemory(BaseMemory):
    """
    Manages event-based memories for personas.
    
    This class handles storage, retrieval, and management of dynamic event-based memories
    such as conversations, actions, observations, and other temporal experiences.
    """
    
    def __init__(self, agent_id: str, user_id: str = "0", max_events: int = 1000):
        """
        Initialize EventMemory for a specific agent and user combination.
        
        Args:
            agent_id: Unique identifier for the agent
            user_id: Unique identifier for the user (defaults to "0" for agent-only memory)
            max_events: Maximum number of events to keep in memory
        """
        super().__init__(agent_id, user_id)
        self.max_events = max_events
        self._events: List[Event] = []
    
    def add_event(self, event_type: str, content: str, 
                  metadata: Optional[Dict[str, Any]] = None, 
                  importance: int = 1) -> Event:
        """
        Add new event to memory.
        
        Args:
            event_type: Type of the event (e.g., 'conversation', 'action', 'observation')
            content: Event content/description
            metadata: Additional metadata for the event
            importance: Importance level (1-10)
            
        Returns:
            The created Event object
        """
        event = Event(
            timestamp=time.time(),
            event_type=event_type,
            content=content,
            metadata=metadata,
            importance=importance
        )
        
        self._events.append(event)
        self._trim_events()
        return event
    
    def get_events(self, 
                   event_type: Optional[str] = None,
                   since: Optional[Union[datetime, float]] = None,
                   until: Optional[Union[datetime, float]] = None,
                   min_importance: Optional[int] = None,
                   limit: Optional[int] = None) -> List[Event]:
        """
        Retrieve events based on filters.
        
        Args:
            event_type: Filter by event type
            since: Get events since this datetime/timestamp
            until: Get events until this datetime/timestamp
            min_importance: Minimum importance level
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        events = self._events
        
        # Filter by event type
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Filter by time range
        if since:
            since_ts = since.timestamp() if isinstance(since, datetime) else since
            events = [e for e in events if e.timestamp >= since_ts]
        
        if until:
            until_ts = until.timestamp() if isinstance(until, datetime) else until
            events = [e for e in events if e.timestamp <= until_ts]
        
        # Filter by importance
        if min_importance:
            events = [e for e in events if e.importance >= min_importance]
        
        # Sort by timestamp (most recent first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            events = events[:limit]
        
        return events
    
    def get_recent_events(self, hours: int = 24, limit: int = 50) -> List[Event]:
        """
        Get recent events within specified hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        since = datetime.now() - timedelta(hours=hours)
        return self.get_events(since=since, limit=limit)
    
    def get_important_events(self, min_importance: int = 7, limit: int = 20) -> List[Event]:
        """
        Get important events.
        
        Args:
            min_importance: Minimum importance level
            limit: Maximum number of events to return
            
        Returns:
            List of important events
        """
        return self.get_events(min_importance=min_importance, limit=limit)
    
    def search_events(self, query: str, case_sensitive: bool = False) -> List[Event]:
        """
        Search events by content.
        
        Args:
            query: Search query string
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of matching events
        """
        if not case_sensitive:
            query = query.lower()
        
        matching_events = []
        for event in self._events:
            content = event.content if case_sensitive else event.content.lower()
            if query in content:
                matching_events.append(event)
        
        return sorted(matching_events, key=lambda e: e.timestamp, reverse=True)
    
    def clear_old_events(self, older_than_days: int = 30) -> int:
        """
        Clear events older than specified days.
        
        Args:
            older_than_days: Remove events older than this many days
            
        Returns:
            Number of events removed
        """
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        initial_count = len(self._events)
        self._events = [e for e in self._events if e.timestamp >= cutoff_time]
        return initial_count - len(self._events)
    
    def get_event_types(self) -> List[str]:
        """
        Get list of all event types in memory.
        
        Returns:
            List of unique event types
        """
        return list(set(event.event_type for event in self._events))
    
    def get_events_count(self) -> int:
        """
        Get total number of events in memory.
        
        Returns:
            Number of events
        """
        return len(self._events)
    
    def clear(self) -> None:
        """Clear all events from memory."""
        self._events.clear()
        self._update_timestamp()
    
    def get_size(self) -> int:
        """
        Get the number of events in memory.
        
        Returns:
            Number of events
        """
        return len(self._events)
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save events to JSON file.
        
        Args:
            file_path: Path to save the events
        """
        events_data = {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "max_events": self.max_events,
            "created_at": self._created_at,
            "events": [event.to_dict() for event in self._events]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'EventMemory':
        """
        Load events from JSON file.
        
        Args:
            file_path: Path to load the events from
            
        Returns:
            EventMemory instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both old format (persona_id) and new format (agent_id, user_id)
        if "agent_id" in data and "user_id" in data:
            instance = cls(data["agent_id"], data["user_id"], data.get("max_events", 1000))
        else:
            # Legacy support: parse persona_id as agent_id:user_id
            persona_id = data["persona_id"]
            if ":" in persona_id:
                agent_id, user_id = persona_id.split(":", 1)
            else:
                agent_id, user_id = persona_id, "0"
            instance = cls(agent_id, user_id, data.get("max_events", 1000))
        
        instance._created_at = data.get("created_at", time.time())
        instance._events = [Event.from_dict(event_data) for event_data in data["events"]]
        return instance
    
    def _trim_events(self) -> None:
        """Trim events to max_events limit, keeping most recent and important."""
        if len(self._events) <= self.max_events:
            return
        
        # Sort by importance (desc) and timestamp (desc)
        self._events.sort(key=lambda e: (e.importance, e.timestamp), reverse=True)
        self._events = self._events[:self.max_events]
    
    def __str__(self) -> str:
        memory_type = "user" if self.is_user_profile else "agent"
        return f"EventMemory(agent_id={self.agent_id}, user_id={self.user_id}, type={memory_type}, events={len(self._events)})" 