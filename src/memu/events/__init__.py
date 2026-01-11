"""
Event-driven orchestration system for MemU.

This module provides a flexible event hook system that allows external
workers (Celery/Redis) to react to memory operations asynchronously.

Architecture:
    EventManager (hub) -> Dispatchers (listeners) -> Workers (Celery tasks)

Usage:
    # Simply import - CeleryDispatcher auto-registers
    from memu.events import event_manager

    # Emit events
    event_manager.emit('on_memory_saved', {
        'resource_url': 'https://example.com/doc.pdf',
        'modality': 'document',
        'user': {'user_id': '123'}
    })
"""

from .manager import EventManager, event_manager

# Import setup to trigger auto-initialization
# This creates and registers the CeleryDispatcher automatically
from . import setup  # noqa: F401

__all__ = ["event_manager", "EventManager"]
