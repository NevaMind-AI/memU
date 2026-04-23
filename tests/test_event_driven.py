"""
Tests for Event-Driven Orchestration System

This test suite verifies the event-driven architecture implementation
for Issue #190: Event-Driven Orchestration with Celery Integration.

Tests cover:
1. EventManager hook system
2. CeleryDispatcher event handling
3. Event emission and dispatch flow
4. Integration with MemoryService
"""

import os
import sys

# ensure Python finds the src folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, Mock, patch

import pytest

from memu.events.dispatcher import CeleryDispatcher
from memu.events.manager import EventManager


class TestEventManager:
    """Test the EventManager hook system."""

    def test_event_manager_initialization(self):
        """EventManager should initialize with supported events."""
        manager = EventManager()

        events = manager.list_events()
        assert "on_memory_saved" in events
        assert "on_memory_updated" in events
        assert "on_memory_deleted" in events
        assert "on_memory_queried" in events

    def test_register_callback(self):
        """Should allow registering callbacks for events."""
        manager = EventManager()
        callback = Mock()

        manager.on("on_memory_saved", callback)

        assert manager.get_listener_count("on_memory_saved") == 1

    def test_emit_event_calls_callback(self):
        """Emitting event should call registered callbacks."""
        manager = EventManager()
        callback = Mock()

        manager.on("on_memory_saved", callback)
        manager.emit("on_memory_saved", {"resource_url": "test.pdf"})

        callback.assert_called_once_with({"resource_url": "test.pdf"})

    def test_multiple_callbacks_for_same_event(self):
        """Multiple callbacks can be registered for the same event."""
        manager = EventManager()
        callback1 = Mock()
        callback2 = Mock()

        manager.on("on_memory_saved", callback1)
        manager.on("on_memory_saved", callback2)

        manager.emit("on_memory_saved", {"data": "test"})

        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_unregister_callback(self):
        """Should allow unregistering callbacks."""
        manager = EventManager()
        callback = Mock()

        manager.on("on_memory_saved", callback)
        manager.off("on_memory_saved", callback)

        manager.emit("on_memory_saved", {"data": "test"})

        callback.assert_not_called()

    def test_register_dispatcher(self):
        """Should register dispatcher with event handler methods."""
        manager = EventManager()

        class TestDispatcher:
            def on_memory_saved(self, data):
                pass

            def on_memory_updated(self, data):
                pass

        dispatcher = TestDispatcher()
        dispatcher.on_memory_saved = Mock()
        dispatcher.on_memory_updated = Mock()

        manager.register_dispatcher(dispatcher)

        # Emit events
        manager.emit("on_memory_saved", {"test": "data1"})
        manager.emit("on_memory_updated", {"test": "data2"})

        dispatcher.on_memory_saved.assert_called_once_with({"test": "data1"})
        dispatcher.on_memory_updated.assert_called_once_with({"test": "data2"})


class TestCeleryDispatcher:
    """Test the CeleryDispatcher implementation."""

    def test_dispatcher_initialization(self):
        """CeleryDispatcher should initialize with enabled state."""
        dispatcher = CeleryDispatcher(enabled=True)

        assert dispatcher.enabled is True

    def test_dispatcher_disabled_skips_dispatch(self):
        """Disabled dispatcher should not dispatch events."""
        dispatcher = CeleryDispatcher(enabled=False)

        result = dispatcher.on_memory_saved({"resource_url": "test.pdf", "modality": "document"})

        assert result is None

    @patch("memu.tasks.process_memory_task")
    def test_on_memory_saved_dispatches_to_celery(self, mock_task):
        """on_memory_saved should dispatch to Celery task."""
        # Mock the task
        mock_async_result = MagicMock()
        mock_async_result.id = "test-task-id-123"
        mock_task.apply_async.return_value = mock_async_result

        dispatcher = CeleryDispatcher(enabled=True)

        event_data = {
            "resource_url": "https://example.com/test.pdf",
            "modality": "document",
            "user": {"user_id": "user_123"},
        }

        task_id = dispatcher.on_memory_saved(event_data)

        # Verify task was called
        mock_task.apply_async.assert_called_once()
        args, _ = mock_task.apply_async.call_args

        # Check task arguments
        assert args[1][0] == "https://example.com/test.pdf"  # resource_url
        assert args[1][1] == "document"  # modality
        assert args[1][2]["user_id"] == "user_123"  # user

        # Check task_id returned
        assert task_id == "test-task-id-123"

    @patch("memu.tasks.process_memory_task")
    def test_on_memory_updated_dispatches_to_celery(self, mock_task):
        """on_memory_updated should dispatch to Celery task."""
        mock_async_result = MagicMock()
        mock_async_result.id = "test-task-id-456"
        mock_task.apply_async.return_value = mock_async_result

        dispatcher = CeleryDispatcher(enabled=True)

        event_data = {"resource_url": "https://example.com/updated.pdf", "modality": "document"}

        task_id = dispatcher.on_memory_updated(event_data)

        mock_task.apply_async.assert_called_once()
        assert task_id == "test-task-id-456"

    def test_on_memory_deleted_logs_event(self):
        """on_memory_deleted should log the event (no processing by default)."""
        dispatcher = CeleryDispatcher(enabled=True)

        result = dispatcher.on_memory_deleted({"memory_id": "123"})

        # For now, delete operations just log (can be extended later)
        assert result is None

    def test_on_memory_queried_logs_event(self):
        """on_memory_queried should log the event (no processing by default)."""
        dispatcher = CeleryDispatcher(enabled=True)

        result = dispatcher.on_memory_queried({"query": "test query"})

        assert result is None

    def test_enable_disable_dispatcher(self):
        """Should be able to enable/disable dispatcher."""
        dispatcher = CeleryDispatcher(enabled=False)

        assert dispatcher.enabled is False

        dispatcher.enable()
        assert dispatcher.enabled is True

        dispatcher.disable()
        assert dispatcher.enabled is False

    def test_set_task_options(self):
        """Should be able to update task dispatch options."""
        dispatcher = CeleryDispatcher()

        dispatcher.set_task_options(priority=5, queue="high-priority")

        assert dispatcher.task_options["priority"] == 5
        assert dispatcher.task_options["queue"] == "high-priority"


class TestEventDrivenIntegration:
    """Integration tests for the event-driven flow."""

    @patch("memu.tasks.process_memory_task")
    def test_end_to_end_event_flow(self, mock_task):
        """Test complete flow: emit event -> dispatcher -> Celery task."""
        # Setup
        manager = EventManager()
        dispatcher = CeleryDispatcher(enabled=True)

        mock_async_result = MagicMock()
        mock_async_result.id = "integration-test-task-id"
        mock_task.apply_async.return_value = mock_async_result

        # Register dispatcher
        manager.register_dispatcher(dispatcher)

        # Emit event
        manager.emit(
            "on_memory_saved",
            {
                "resource_url": "https://example.com/integration-test.pdf",
                "modality": "document",
                "user": {"user_id": "integration_user"},
            },
        )

        # Verify task was dispatched
        mock_task.apply_async.assert_called_once()
        args = mock_task.apply_async.call_args[1]["args"]

        assert args[0] == "https://example.com/integration-test.pdf"
        assert args[1] == "document"
        assert args[2]["user_id"] == "integration_user"

    def test_multiple_dispatchers(self):
        """Multiple dispatchers can listen to the same event."""
        manager = EventManager()

        dispatcher1 = Mock()
        dispatcher1.on_memory_saved = Mock()

        dispatcher2 = Mock()
        dispatcher2.on_memory_saved = Mock()

        manager.register_dispatcher(dispatcher1)
        manager.register_dispatcher(dispatcher2)

        manager.emit("on_memory_saved", {"resource_url": "test.pdf"})

        dispatcher1.on_memory_saved.assert_called_once()
        dispatcher2.on_memory_saved.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
