#!/usr/bin/env python
"""
MemU Celery Worker Entry Point

This is the main entry point for starting Celery workers that process
memory operation events dispatched via the event-driven orchestration system.

Usage:
    # Start worker
    celery -A worker worker --loglevel=info

    # Start worker with specific concurrency
    celery -A worker worker --concurrency=4 --loglevel=info

    # Start worker with specific queue
    celery -A worker worker --queue=memory-processing --loglevel=info

Architecture:
    MemoryService.memorize(background=True)
        ↓
    EventManager.emit('on_memory_saved', data)
        ↓
    CeleryDispatcher receives event
        ↓
    Dispatches to process_memory_task.delay()
        ↓
    Celery Worker (THIS FILE) consumes task
        ↓
    MemoryService.memorize() executes in background

Environment Variables:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    REDIS_PASSWORD: Redis password (optional)
    CELERY_LOG_LEVEL: Logging level (default: INFO)
    CELERY_LOG_JSON: Use JSON logging (default: true)
    MEMU_AUTO_INIT_EVENTS: Auto-initialize event system (default: true)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from memu import tasks  # noqa: F401
from memu.celery_app import celery_app
from memu.events.setup import init_event_system

init_event_system(celery=True)

app = celery_app

if __name__ == "__main__":
    print("=" * 60)
    print("MemU Celery Worker")
    print("=" * 60)
    print(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
    print(f"Log Level: {os.getenv('CELERY_LOG_LEVEL', 'INFO')}")
    print(f"JSON Logging: {os.getenv('CELERY_LOG_JSON', 'true')}")
    print("=" * 60)
    print("\nStarting worker...")
    print("Use Ctrl+C to stop\n")

    celery_app.worker_main([
        "worker",
        "--loglevel=info",
    ])
