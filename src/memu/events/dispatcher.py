"""
Celery Dispatcher - Event handler that dispatches events to Celery workers.

This module implements the CeleryDispatcher class which listens to memory
operation events and pushes them to Redis/Celery for background processing.

Architecture:
    EventManager emits event -> CeleryDispatcher receives -> Celery task queued

Example:
    >>> from memu.events import event_manager
    >>> from memu.events.dispatcher import CeleryDispatcher
    >>>
    >>> # Register dispatcher
    >>> dispatcher = CeleryDispatcher()
    >>> event_manager.register_dispatcher(dispatcher)
    >>>
    >>> # Emit event (dispatcher auto-handles)
    >>> event_manager.emit('on_memory_saved', {
    ...     'resource_url': 'https://example.com/doc.pdf',
    ...     'modality': 'document',
    ...     'user': {'user_id': '123'}
    ... })
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CeleryDispatcher:
    """
    Dispatcher that pushes memory operation events to Celery workers.

    This class implements the event hooks (on_memory_saved, on_memory_updated, etc.)
    and dispatches them to background Celery tasks for asynchronous processing.

    The dispatcher can handle various memory operation events and route them
    to appropriate Celery tasks based on the event type and payload.

    Attributes:
        enabled: Whether the dispatcher is active
        task_options: Default options for Celery task dispatch

    Example:
        >>> dispatcher = CeleryDispatcher(enabled=True)
        >>> dispatcher.on_memory_saved({
        ...     'resource_url': 'https://example.com/test.pdf',
        ...     'modality': 'document',
        ...     'user': {'user_id': 'user_123'}
        ... })
        # Task queued with ID: abc-123-def
    """

    def __init__(self, event_manager=None, enabled: bool = True, task_options: dict[str, Any] | None = None):
        """
        Initialize the Celery dispatcher and auto-register with EventManager.

        Args:
            event_manager: EventManager instance to register with (auto-imports if None)
            enabled: Whether to actively dispatch events to Celery
            task_options: Default options for task dispatch (priority, queue, etc.)
        """
        self.enabled = enabled
        self.task_options = task_options or {}

        # Auto-register with EventManager
        if event_manager is None:
            from .manager import event_manager as default_manager

            event_manager = default_manager

        event_manager.register_dispatcher(self)

        logger.info(
            f"CeleryDispatcher initialized and registered (enabled={enabled})",
            extra={
                "enabled": enabled,
                "task_options": task_options,
                "registered_dispatchers": len(event_manager._dispatchers),
            },
        )

    def _dispatch_to_celery(
        self, event_name: str, data: dict[str, Any], task_name: str = "memu.tasks.process_memory"
    ) -> str | None:
        """
        Internal method to dispatch event data to a Celery task.

        Args:
            event_name: The event that triggered this dispatch
            data: Event payload to send to worker
            task_name: Celery task name to invoke

        Returns:
            Task ID if dispatched successfully, None otherwise
        """
        if not self.enabled:
            logger.debug(f"Dispatcher disabled, skipping event: {event_name}")
            return None

        try:
            # Import here to avoid circular dependency
            from memu.tasks import process_memory_task

            # Extract task parameters from event data
            resource_url = data.get("resource_url")
            modality = data.get("modality")
            user = data.get("user")

            if not resource_url or not modality:
                logger.error(
                    f"Invalid event data for {event_name}: missing required fields",
                    extra={"event": event_name, "data": data},
                )
                return None

            # Dispatch to Celery using existing task
            task = process_memory_task.apply_async(args=[resource_url, modality, user], **self.task_options)

            logger.info(
                f"Event '{event_name}' dispatched to Celery",
                extra={
                    "event": event_name,
                    "task_id": task.id,
                    "resource_url": resource_url,
                    "modality": modality,
                    "user_id": user.get("user_id") if user else None,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to dispatch event '{event_name}' to Celery",
                exc_info=True,
                extra={"event": event_name, "error": str(e)},
            )
            return None
        else:
            return task.id

    def on_memory_saved(self, data: dict[str, Any]) -> str | None:
        """
        Handle 'on_memory_saved' event.

        This event is fired when new memory is successfully saved to the database.
        The dispatcher queues the memory for background processing (embedding,
        indexing, graph analysis, etc.).

        Args:
            data: Event payload containing:
                - resource_url: URL of the resource to process
                - modality: Type of content (document, image, video, etc.)
                - user: User context dictionary (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Task ID if dispatched successfully

        Example:
            >>> dispatcher.on_memory_saved({
            ...     'resource_url': 'https://example.com/paper.pdf',
            ...     'modality': 'document',
            ...     'user': {'user_id': '123'},
            ...     'metadata': {'title': 'Research Paper'}
            ... })
            'abc-123-def-456'
        """
        logger.debug("on_memory_saved event received", extra={"resource_url": data.get("resource_url")})

        return self._dispatch_to_celery(event_name="on_memory_saved", data=data, task_name="memu.tasks.process_memory")

    def on_memory_updated(self, data: dict[str, Any]) -> str | None:
        """
        Handle 'on_memory_updated' event.

        This event is fired when existing memory is modified. The dispatcher
        can re-process the memory to update embeddings, re-index, or sync
        with external databases.

        Args:
            data: Event payload (same structure as on_memory_saved)

        Returns:
            Task ID if dispatched successfully
        """
        logger.debug("on_memory_updated event received", extra={"resource_url": data.get("resource_url")})

        return self._dispatch_to_celery(
            event_name="on_memory_updated", data=data, task_name="memu.tasks.process_memory"
        )

    def on_memory_deleted(self, data: dict[str, Any]) -> str | None:
        """
        Handle 'on_memory_deleted' event.

        This event is fired when memory is removed. The dispatcher can queue
        cleanup tasks (remove from indexes, delete cached embeddings, etc.).

        Args:
            data: Event payload containing memory identifier and metadata

        Returns:
            Task ID if dispatched successfully
        """
        logger.debug("on_memory_deleted event received", extra={"memory_id": data.get("memory_id")})

        # For delete operations, we might want a different task
        # For now, log the event (can extend later)
        logger.info("Memory deletion event (no background processing configured)", extra={"data": data})

        return None

    def on_memory_queried(self, data: dict[str, Any]) -> str | None:
        """
        Handle 'on_memory_queried' event.

        This event is fired when memory is searched/retrieved. The dispatcher
        can log analytics, update access patterns, or trigger related processing.

        Args:
            data: Event payload containing query details

        Returns:
            Task ID if dispatched successfully
        """
        logger.debug("on_memory_queried event received", extra={"query": data.get("query")})

        # For query operations, typically no background processing needed
        # Can be used for analytics, logging, etc.
        logger.info("Memory query event (no background processing configured)", extra={"data": data})

        return None

    def enable(self) -> None:
        """Enable the dispatcher to actively dispatch events."""
        self.enabled = True
        logger.info("CeleryDispatcher enabled")

    def disable(self) -> None:
        """Disable the dispatcher (events will be logged but not dispatched)."""
        self.enabled = False
        logger.info("CeleryDispatcher disabled")

    def set_task_options(self, **options) -> None:
        """
        Update default task dispatch options.

        Args:
            **options: Celery task options (priority, queue, countdown, etc.)

        Example:
            >>> dispatcher.set_task_options(priority=5, queue='high-priority')
        """
        self.task_options.update(options)
        logger.info("Updated task options", extra={"task_options": self.task_options})
