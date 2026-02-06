"""
Event system initialization and setup.

This module provides utilities to initialize the event-driven orchestration
system with the appropriate dispatchers.

Usage:
    from memu.events.setup import init_event_system

    # Initialize with Celery dispatcher (auto-registers)
    init_event_system()

    # Or manually create dispatcher (auto-registers)
    from memu.events.dispatcher import CeleryDispatcher
    dispatcher = CeleryDispatcher()  # Automatically registers itself
"""

import logging
import os

from .dispatcher import CeleryDispatcher
from .manager import event_manager

logger = logging.getLogger(__name__)


def init_event_system(celery: bool = True, celery_options: dict | None = None) -> None:
    """
    Initialize the event system with dispatchers.

    This function sets up the event-driven orchestration by creating
    a CeleryDispatcher which automatically registers itself with the
    global event manager.

    Args:
        celery: Whether to create the Celery dispatcher
        celery_options: Options to pass to CeleryDispatcher constructor

    Example:
        >>> from memu.events.setup import init_event_system
        >>> init_event_system(celery=True)
        >>> # Event system ready - CeleryDispatcher auto-registered
    """
    if celery:
        options = celery_options or {}
        # CeleryDispatcher auto-registers itself on instantiation
        CeleryDispatcher(event_manager=event_manager, **options)

        logger.info(
            "Event system initialized with CeleryDispatcher",
            extra={"dispatcher_count": len(event_manager._dispatchers)},
        )
    else:
        logger.info("Event system initialized without dispatchers")


# Auto-initialize on import (can be disabled via environment variable)
if os.getenv("MEMU_AUTO_INIT_EVENTS", "true").lower() == "true":
    try:
        init_event_system(celery=True)
        logger.debug(f"Event system auto-initialized: {len(event_manager._dispatchers)} dispatcher(s) registered")
    except Exception as e:
        logger.error(f"Failed to auto-initialize event system: {e}", exc_info=True)
