"""
Tests for the memory module.
"""

import json
import time
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from personalab.memory import BaseMemory, ProfileMemory, EventMemory, Event


class TestEvent:
    """Test cases for Event class."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        timestamp = time.time()
        event = Event(
            timestamp=timestamp,
            event_type="conversation",
            content="Hello world",
            metadata={"user": "test"},
            importance=5
        )
        
        assert event.timestamp == timestamp
        assert event.event_type == "conversation"
        assert event.content == "Hello world"
        assert event.metadata == {"user": "test"}
        assert event.importance == 5
    
    def test_event_to_dict(self):
        """Test event to dictionary conversion."""
        event = Event(
            timestamp=1234567890.0,
            event_type="action",
            content="Test action",
            importance=3
        )
        
        expected = {
            "timestamp": 1234567890.0,
            "event_type": "action",
            "content": "Test action",
            "metadata": None,
            "importance": 3
        }
        
        assert event.to_dict() == expected
    
    def test_event_from_dict(self):
        """Test event creation from dictionary."""
        data = {
            "timestamp": 1234567890.0,
            "event_type": "observation",
            "content": "Saw something interesting",
            "metadata": {"location": "room1"},
            "importance": 7
        }
        
        event = Event.from_dict(data)
        assert event.timestamp == 1234567890.0
        assert event.event_type == "observation"
        assert event.content == "Saw something interesting"
        assert event.metadata == {"location": "room1"}
        assert event.importance == 7
    
    def test_event_datetime_property(self):
        """Test datetime property."""
        timestamp = 1234567890.0
        event = Event(timestamp=timestamp, event_type="test", content="test")
        expected_dt = datetime.fromtimestamp(timestamp)
        assert event.datetime == expected_dt
    
    def test_event_str(self):
        """Test string representation."""
        event = Event(
            timestamp=1234567890.0,
            event_type="test",
            content="Test content"
        )
        str_repr = str(event)
        assert "Event(test): Test content" in str_repr
        assert "2009-02-13 23:31:30" in str_repr  # Expected datetime string


class TestBaseMemory:
    """Test cases for BaseMemory abstract class."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseMemory cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseMemory("test_persona")
    
    def test_memory_info_structure(self):
        """Test that memory info returns correct structure."""
        pm = ProfileMemory("test_persona")
        info = pm.get_memory_info()
        
        assert info["persona_id"] == "test_persona"
        assert info["memory_type"] == "ProfileMemory"
        assert "created_at" in info
        assert "updated_at" in info
        assert "size" in info
        assert isinstance(info["size"], int)
    
    def test_timestamps_inheritance(self):
        """Test that timestamp functionality is inherited correctly."""
        pm = ProfileMemory("test_persona")
        em = EventMemory("test_persona")
        
        # Both should have timestamps
        assert hasattr(pm, 'created_at')
        assert hasattr(pm, 'updated_at')
        assert hasattr(em, 'created_at')
        assert hasattr(em, 'updated_at')
        
        # Timestamps should be datetime objects
        assert isinstance(pm.created_at, datetime)
        assert isinstance(pm.updated_at, datetime)
        assert isinstance(em.created_at, datetime)
        assert isinstance(em.updated_at, datetime)


class TestProfileMemory:
    """Test cases for ProfileMemory class."""
    
    def test_init_empty(self):
        """Test initialization with empty profile."""
        pm = ProfileMemory("persona_1")
        assert pm.persona_id == "persona_1"
        assert pm.get_profile() == {}
    
    def test_init_with_data(self):
        """Test initialization with profile data."""
        data = {"name": "Alice", "age": 25, "personality": "friendly"}
        pm = ProfileMemory("persona_1", data)
        assert pm.persona_id == "persona_1"
        assert pm.get_profile() == data
    
    def test_get_field(self):
        """Test getting specific field."""
        pm = ProfileMemory("persona_1", {"name": "Bob", "age": 30})
        assert pm.get_field("name") == "Bob"
        assert pm.get_field("age") == 30
        assert pm.get_field("unknown") is None
        assert pm.get_field("unknown", "default") == "default"
    
    def test_set_field(self):
        """Test setting specific field."""
        pm = ProfileMemory("persona_1")
        pm.set_field("name", "Charlie")
        pm.set_field("skills", ["python", "ai"])
        
        assert pm.get_field("name") == "Charlie"
        assert pm.get_field("skills") == ["python", "ai"]
    
    def test_update_profile(self):
        """Test updating multiple fields."""
        pm = ProfileMemory("persona_1", {"name": "Alice"})
        updates = {"age": 28, "location": "NYC", "name": "Alice Smith"}
        pm.update_profile(updates)
        
        profile = pm.get_profile()
        assert profile["name"] == "Alice Smith"
        assert profile["age"] == 28
        assert profile["location"] == "NYC"
    
    def test_remove_field(self):
        """Test removing field."""
        pm = ProfileMemory("persona_1", {"name": "Dave", "age": 35, "city": "LA"})
        
        # Remove existing field
        result = pm.remove_field("age")
        assert result is True
        assert "age" not in pm.get_profile()
        
        # Try to remove non-existing field
        result = pm.remove_field("nonexistent")
        assert result is False
    
    def test_has_field(self):
        """Test checking field existence."""
        pm = ProfileMemory("persona_1", {"name": "Eve", "skills": []})
        assert pm.has_field("name") is True
        assert pm.has_field("skills") is True
        assert pm.has_field("age") is False
    
    def test_save_and_load_file(self):
        """Test saving and loading from file."""
        pm = ProfileMemory("persona_1", {"name": "Frank", "age": 40})
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Save profile
            pm.save_to_file(temp_file)
            
            # Load profile
            loaded_pm = ProfileMemory.load_from_file(temp_file)
            
            assert loaded_pm.persona_id == "persona_1"
            assert loaded_pm.get_profile() == {"name": "Frank", "age": 40}
        finally:
            os.unlink(temp_file)
    
    def test_timestamps(self):
        """Test creation and update timestamps."""
        pm = ProfileMemory("persona_1")
        created_time = pm.created_at
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        pm.set_field("test", "value")
        updated_time = pm.updated_at
        
        assert isinstance(created_time, datetime)
        assert isinstance(updated_time, datetime)
        assert updated_time > created_time
    
    def test_str_representation(self):
        """Test string representation."""
        pm = ProfileMemory("persona_1", {"name": "Grace", "age": 33})
        str_repr = str(pm)
        assert "ProfileMemory(persona_id=persona_1, fields=2)" == str_repr
    
    def test_clear(self):
        """Test clearing profile data."""
        pm = ProfileMemory("persona_1", {"name": "Test", "age": 25, "city": "NYC"})
        assert pm.get_size() == 3
        
        pm.clear()
        assert pm.get_size() == 0
        assert pm.get_profile() == {}
    
    def test_get_size(self):
        """Test getting profile size."""
        pm = ProfileMemory("persona_1")
        assert pm.get_size() == 0
        
        pm.set_field("name", "Test")
        assert pm.get_size() == 1
        
        pm.update_profile({"age": 30, "city": "SF"})
        assert pm.get_size() == 3


class TestEventMemory:
    """Test cases for EventMemory class."""
    
    def test_init(self):
        """Test initialization."""
        em = EventMemory("persona_1", max_events=500)
        assert em.persona_id == "persona_1"
        assert em.max_events == 500
        assert em.get_events_count() == 0
    
    def test_add_event(self):
        """Test adding events."""
        em = EventMemory("persona_1")
        
        event = em.add_event(
            event_type="conversation",
            content="Hello there!",
            metadata={"user": "human"},
            importance=5
        )
        
        assert isinstance(event, Event)
        assert event.event_type == "conversation"
        assert event.content == "Hello there!"
        assert event.metadata == {"user": "human"}
        assert event.importance == 5
        assert em.get_events_count() == 1
    
    def test_get_events_no_filter(self):
        """Test getting all events."""
        em = EventMemory("persona_1")
        em.add_event("type1", "content1", importance=3)
        em.add_event("type2", "content2", importance=7)
        
        events = em.get_events()
        assert len(events) == 2
        # Should be sorted by timestamp (most recent first)
        assert events[0].content == "content2"
        assert events[1].content == "content1"
    
    def test_get_events_by_type(self):
        """Test filtering events by type."""
        em = EventMemory("persona_1")
        em.add_event("conversation", "Hello")
        em.add_event("action", "Walked")
        em.add_event("conversation", "Goodbye")
        
        conversations = em.get_events(event_type="conversation")
        assert len(conversations) == 2
        assert all(e.event_type == "conversation" for e in conversations)
    
    def test_get_events_by_importance(self):
        """Test filtering events by importance."""
        em = EventMemory("persona_1")
        em.add_event("test", "low", importance=2)
        em.add_event("test", "medium", importance=5)
        em.add_event("test", "high", importance=8)
        
        important_events = em.get_events(min_importance=6)
        assert len(important_events) == 1
        assert important_events[0].content == "high"
    
    def test_get_events_by_time_range(self):
        """Test filtering events by time range."""
        em = EventMemory("persona_1")
        
        # Add events with specific timestamps
        old_time = time.time() - 3600  # 1 hour ago
        recent_time = time.time() - 1800  # 30 minutes ago
        
        with patch('time.time', return_value=old_time):
            em.add_event("old", "old event")
        
        with patch('time.time', return_value=recent_time):
            em.add_event("recent", "recent event")
        
        # Get events since 45 minutes ago
        since_time = time.time() - 2700
        recent_events = em.get_events(since=since_time)
        assert len(recent_events) == 1
        assert recent_events[0].content == "recent event"
    
    def test_get_events_with_limit(self):
        """Test limiting number of returned events."""
        em = EventMemory("persona_1")
        for i in range(10):
            em.add_event("test", f"content {i}")
        
        limited_events = em.get_events(limit=5)
        assert len(limited_events) == 5
    
    def test_get_recent_events(self):
        """Test getting recent events."""
        em = EventMemory("persona_1")
        
        # Add old event
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        with patch('time.time', return_value=old_time):
            em.add_event("old", "old event")
        
        # Add recent event
        em.add_event("recent", "recent event")
        
        recent_events = em.get_recent_events(hours=24)
        assert len(recent_events) == 1
        assert recent_events[0].content == "recent event"
    
    def test_get_important_events(self):
        """Test getting important events."""
        em = EventMemory("persona_1")
        em.add_event("test", "normal", importance=5)
        em.add_event("test", "important", importance=8)
        em.add_event("test", "critical", importance=10)
        
        important_events = em.get_important_events(min_importance=7)
        assert len(important_events) == 2
        contents = [e.content for e in important_events]
        assert "important" in contents
        assert "critical" in contents
    
    def test_search_events(self):
        """Test searching events by content."""
        em = EventMemory("persona_1")
        em.add_event("test", "The quick brown fox")
        em.add_event("test", "jumps over the lazy dog")
        em.add_event("test", "Python is awesome")
        
        # Case insensitive search
        results = em.search_events("quick")
        assert len(results) == 1
        assert "quick" in results[0].content
        
        # Case sensitive search
        results = em.search_events("QUICK", case_sensitive=True)
        assert len(results) == 0
        
        results = em.search_events("the")
        assert len(results) == 2
    
    def test_clear_old_events(self):
        """Test clearing old events."""
        em = EventMemory("persona_1")
        
        # Add old events
        old_time = time.time() - (35 * 24 * 3600)  # 35 days ago
        with patch('time.time', return_value=old_time):
            em.add_event("old", "old event 1")
            em.add_event("old", "old event 2")
        
        # Add recent event
        em.add_event("recent", "recent event")
        
        assert em.get_events_count() == 3
        
        # Clear events older than 30 days
        removed_count = em.clear_old_events(older_than_days=30)
        assert removed_count == 2
        assert em.get_events_count() == 1
    
    def test_get_event_types(self):
        """Test getting unique event types."""
        em = EventMemory("persona_1")
        em.add_event("conversation", "hello")
        em.add_event("action", "walk")
        em.add_event("conversation", "goodbye")
        em.add_event("observation", "saw cat")
        
        event_types = em.get_event_types()
        assert set(event_types) == {"conversation", "action", "observation"}
    
    def test_max_events_trim(self):
        """Test automatic trimming when max_events is reached."""
        em = EventMemory("persona_1", max_events=3)
        
        # Add events with different importance levels
        em.add_event("test", "content1", importance=5)
        em.add_event("test", "content2", importance=3)  # Should be removed first
        em.add_event("test", "content3", importance=8)
        em.add_event("test", "content4", importance=6)  # This should trigger trimming
        
        # Should only have 3 events, with the least important removed
        assert em.get_events_count() == 3
        events = em.get_events()
        contents = [e.content for e in events]
        assert "content2" not in contents  # Lowest importance should be removed
    
    def test_save_and_load_file(self):
        """Test saving and loading events from file."""
        em = EventMemory("persona_1", max_events=100)
        em.add_event("conversation", "Hello", metadata={"user": "test"}, importance=7)
        em.add_event("action", "Walked", importance=3)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Save events
            em.save_to_file(temp_file)
            
            # Load events
            loaded_em = EventMemory.load_from_file(temp_file)
            
            assert loaded_em.persona_id == "persona_1"
            assert loaded_em.max_events == 100
            assert loaded_em.get_events_count() == 2
            
            events = loaded_em.get_events()
            assert events[0].content == "Walked"  # Most recent first
            assert events[1].content == "Hello"
        finally:
            os.unlink(temp_file)
    
    def test_str_representation(self):
        """Test string representation."""
        em = EventMemory("persona_1")
        em.add_event("test", "content")
        str_repr = str(em)
        assert str_repr == "EventMemory(persona_id=persona_1, events=1)"
    
    def test_clear(self):
        """Test clearing all events."""
        em = EventMemory("persona_1")
        em.add_event("test", "content1")
        em.add_event("test", "content2")
        em.add_event("test", "content3")
        
        assert em.get_size() == 3
        em.clear()
        assert em.get_size() == 0
        assert em.get_events() == []
    
    def test_get_size(self):
        """Test getting memory size."""
        em = EventMemory("persona_1")
        assert em.get_size() == 0
        
        em.add_event("test", "content1")
        assert em.get_size() == 1
        
        em.add_event("test", "content2")
        assert em.get_size() == 2
        
        # Test that get_size and get_events_count return same value
        assert em.get_size() == em.get_events_count() 