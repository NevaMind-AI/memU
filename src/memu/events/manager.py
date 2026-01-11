"""
Event Manager - Central hub for the event-driven orchestration system.

This module implements the hook system that allows MemU to dispatch events
to external workers whenever memory operations occur.

Supported Events:
    - on_memory_saved: Fired when new memory is created
    - on_memory_updated: Fired when existing memory is modified
    - on_memory_deleted: Fired when memory is removed
    - on_memory_queried: Fired when memory is searched/retrieved
"""

import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventManager:
    """
    Central event manager for dispatching memory operation events.

    This class implements a simple pub-sub pattern where dispatchers
    can register to listen for specific events.

    Example:
        >>> manager = EventManager()
        >>> manager.on('on_memory_saved', lambda data: print(f"Saved: {data}"))
        >>> manager.emit('on_memory_saved', {'resource_url': 'test.pdf'})
    """

    def __init__(self):
        """Initialize the event manager with empty listener registry."""
        self._listeners: Dict[str, List[Callable]] = {
            'on_memory_saved': [],
            'on_memory_updated': [],
            'on_memory_deleted': [],
            'on_memory_queried': [],
        }
        self._dispatchers: List[Any] = []

    def on(self, event: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for a specific event.

        Args:
            event: Event name (e.g., 'on_memory_saved')
            callback: Function to call when event is emitted

        Example:
            >>> def handle_save(data):
            ...     print(f"Memory saved: {data['resource_url']}")
            >>> manager.on('on_memory_saved', handle_save)
        """
        if event not in self._listeners:
            self._listeners[event] = []

        self._listeners[event].append(callback)
        logger.debug(f"Registered callback for event: {event}")

    def off(self, event: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Unregister a callback for a specific event.

        Args:
            event: Event name
            callback: The callback function to remove
        """
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)
            logger.debug(f"Unregistered callback for event: {event}")

    def emit(self, event: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered listeners.

        This method calls all registered callbacks for the specified event,
        passing the data payload to each callback.

        Args:
            event: Event name to emit
            data: Event payload data

        Example:
            >>> manager.emit('on_memory_saved', {
            ...     'resource_url': 'https://example.com/doc.pdf',
            ...     'modality': 'document',
            ...     'user': {'user_id': '123'}
            ... })
        """
        if event not in self._listeners:
            logger.warning(f"Attempted to emit unknown event: {event}")
            return

        logger.info(f"Emitting event: {event}", extra={"event": event, "data": data})

        # Call all registered callbacks
        for callback in self._listeners[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(
                    f"Error in event callback for {event}",
                    exc_info=True,
                    extra={"event": event, "error": str(e)}
                )

    def register_dispatcher(self, dispatcher: Any) -> None:
        """
        Register a dispatcher (e.g., CeleryDispatcher) to handle events.

        A dispatcher must implement methods matching event names:
        - on_memory_saved(data)
        - on_memory_updated(data)
        - on_memory_deleted(data)
        - on_memory_queried(data)

        Args:
            dispatcher: Dispatcher instance with event handler methods

        Example:
            >>> from memu.events.dispatcher import CeleryDispatcher
            >>> celery_dispatcher = CeleryDispatcher()
            >>> manager.register_dispatcher(celery_dispatcher)
        """
        # Auto-register dispatcher methods as event callbacks
        for event in self._listeners.keys():
            if hasattr(dispatcher, event):
                handler = getattr(dispatcher, event)
                self.on(event, handler)
                logger.info(f"Registered dispatcher method: {event}")

        self._dispatchers.append(dispatcher)
        logger.info(f"Registered dispatcher: {dispatcher.__class__.__name__}")

    def unregister_dispatcher(self, dispatcher: Any) -> None:
        """
        Unregister a dispatcher from handling events.

        Args:
            dispatcher: The dispatcher instance to remove
        """
        if dispatcher in self._dispatchers:
            # Unregister all methods
            for event in self._listeners.keys():
                if hasattr(dispatcher, event):
                    handler = getattr(dispatcher, event)
                    self.off(event, handler)

            self._dispatchers.remove(dispatcher)
            logger.info(f"Unregistered dispatcher: {dispatcher.__class__.__name__}")

    def list_events(self) -> List[str]:
        """
        Get list of supported event names.

        Returns:
            List of event names
        """
        return list(self._listeners.keys())

    def get_listener_count(self, event: str) -> int:
        """
        Get number of listeners for a specific event.

        Args:
            event: Event name

        Returns:
            Number of registered listeners
        """
        return len(self._listeners.get(event, []))

event_manager = EventManager()
