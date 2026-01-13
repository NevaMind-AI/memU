"""
Event-Driven Orchestration Demo

This script demonstrates the event-driven architecture implemented
for Issue #190: Event-Driven Orchestration with Celery Integration.

Requirements:
1. Redis server running (localhost:6379 or REDIS_URL env var)
2. Celery worker running (celery -A worker worker --loglevel=info)

Usage:
    python examples/event_driven_demo.py
"""

import asyncio
import os
import sys

# add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from memu.app.service import MemoryService
from memu.events import event_manager
from memu.events.dispatcher import CeleryDispatcher
from memu.events.setup import init_event_system


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


async def demo_event_driven_flow():
    """
    Demonstrate the complete event-driven flow.

    Flow:
        1. Initialize event system with CeleryDispatcher
        2. Emit memory operation event
        3. CeleryDispatcher catches event
        4. Dispatches to Celery worker
        5. Worker processes memory in background
    """
    print_section("Event-Driven Orchestration Demo")

    print("Step 1: Initializing event system...")
    init_event_system(celery=True)
    print("Event system initialized")
    print(f"   - Registered dispatchers: {len(event_manager._dispatchers)}")
    print(f"   - Supported events: {', '.join(event_manager.list_events())}")

    print("\nStep 2: Creating MemoryService instance...")
    service = MemoryService()
    print("MemoryService created")

    print("\nStep 3: Submitting memory for background processing...")
    print("   (Using event-driven dispatch)")

    result = await service.memorize(
        resource_url="https://example.com/event-driven-demo.pdf",
        modality="document",
        user={"user_id": "demo_user_123"},
        background=True,  # triggers event emission
    )

    print("Event emitted and dispatched")
    print(f"   - Status: {result.get('status')}")
    print(f"   - Message: {result.get('message')}")
    print(f"   - Event: {result.get('event')}")
    print(f"   - Resource: {result.get('resource_url')}")

    print_section("Event Flow Visualization")
    print("1. MemoryService.memorize(background=True)")
    print("   ↓")
    print("2. EventManager.emit('on_memory_saved', data)")
    print("   ↓")
    print("3. CeleryDispatcher.on_memory_saved(data)")
    print("   ↓")
    print("4. process_memory_task.delay(...) → Redis Queue")
    print("   ↓")
    print("5. Celery Worker consumes task")
    print("   ↓")
    print("6. MemoryService.memorize() executes in background")

    print_section("Custom Event Listener Demo")

    custom_events = []

    def custom_listener(data):
        """Custom event listener for demonstration."""
        custom_events.append(data)
        print("Custom listener received event!")
        print(f"   - Resource: {data.get('resource_url')}")
        print(f"   - Modality: {data.get('modality')}")

    # Register custom listener
    event_manager.on("on_memory_saved", custom_listener)
    print("Registered custom listener")

    # Emit another event
    print("\nEmitting event with custom listener...")
    await service.memorize(
        resource_url="https://example.com/custom-listener-test.pdf",
        modality="document",
        user={"user_id": "demo_user_456"},
        background=True,
    )

    print(f"\nCustom listener captured {len(custom_events)} event(s)")

    print_section("Dispatcher Status")
    for dispatcher in event_manager._dispatchers:
        if isinstance(dispatcher, CeleryDispatcher):
            print("CeleryDispatcher:")
            print(f"   - Enabled: {dispatcher.enabled}")
            print(f"   - Task Options: {dispatcher.task_options}")

    print_section("Demo Complete")
    print("Event-driven orchestration system working correctly!")
    print("\nNext steps:")
    print("1. Start Celery worker: celery -A worker worker --loglevel=info")
    print("2. Check worker logs to see background task execution")
    print("3. Verify tasks are being processed in the background")


if __name__ == "__main__":
    print("""
MemU Event-Driven Orchestration Demo
Issue #190: Event-Driven Orchestration with Celery
    """)

    print("Prerequisites:")
    print("  Redis server running (default: localhost:6379)")
    print("  Celery worker running (celery -A worker worker --loglevel=info)")
    print("\nStarting demo...\n")

    asyncio.run(demo_event_driven_flow())
