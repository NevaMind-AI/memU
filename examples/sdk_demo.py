#!/usr/bin/env python3
"""
MemU SDK Demo - Complete Example

This example demonstrates the full workflow of using the MemU Python SDK
to memorize content and retrieve memories.

Requirements:
    - Set MEMU_API_KEY environment variable with your API key

Usage:
    export MEMU_API_KEY=your_api_key
    python examples/sdk_demo.py
"""

from __future__ import annotations

import asyncio
import os
import sys

# Add src to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from memu.sdk import MemUClient
from memu.sdk.client import MemUAuthenticationError, MemUClientError


async def demo_cloud_api() -> None:  # noqa: C901
    """
    Demonstrate the MemU Cloud SDK workflow.

    This function shows:
    1. How to initialize the client
    2. How to memorize content
    3. How to list categories
    4. How to retrieve memories with queries
    """
    api_key = os.environ.get("MEMU_API_KEY")
    if not api_key:
        print("❌ MEMU_API_KEY environment variable not set")
        print("   Please get your API key from https://memu.so")
        print("   Then run: export MEMU_API_KEY=your_api_key")
        return

    print("=" * 60)
    print("🚀 MemU SDK Demo - Cloud API")
    print("=" * 60)

    # Demo user and agent IDs
    user_id = "sdk_demo_user"
    agent_id = "sdk_demo_agent"

    try:
        async with MemUClient(api_key=api_key) as client:
            # =========================================================
            # Step 1: Memorize a conversation
            # =========================================================
            print("\n📝 Step 1: Memorizing conversation...")

            # Sample conversation to memorize
            conversation = [
                {"role": "user", "content": "I really love Italian food, especially pasta."},
                {"role": "assistant", "content": "That's great! What's your favorite pasta dish?"},
                {"role": "user", "content": "I love carbonara! It's my absolute favorite."},
                {"role": "assistant", "content": "Carbonara is delicious! Do you cook it at home?"},
                {"role": "user", "content": "Sometimes, but I prefer dining out at authentic Italian restaurants."},
            ]

            result = await client.memorize(
                conversation=conversation,
                user_id=user_id,
                agent_id=agent_id,
                user_name="Demo User",
                agent_name="MemU Assistant",
                wait_for_completion=False,  # Don't wait, just get task ID
            )

            print(f"   ✅ Task submitted: {result.task_id}")
            print("   Status: Memorization in progress...")

            # =========================================================
            # Step 2: Check task status
            # =========================================================
            print("\n⏳ Step 2: Checking task status...")

            if result.task_id:
                status = await client.get_task_status(result.task_id)
                print(f"   Task ID: {status.task_id}")
                print(f"   Status: {status.status}")
                if status.progress:
                    print(f"   Progress: {status.progress}%")

            # =========================================================
            # Step 3: List categories
            # =========================================================
            print("\n📂 Step 3: Listing categories...")

            try:
                categories = await client.list_categories(user_id=user_id)
                print(f"   Found {len(categories)} categories:")
                for cat in categories[:5]:
                    name = cat.name if hasattr(cat, "name") else cat.get("name", "Unknown")
                    summary = cat.summary if hasattr(cat, "summary") else cat.get("summary", "")
                    print(f"      - {name}: {(summary or '')[:50]}...")
            except MemUClientError as e:
                print(f"   Note: {e.message}")

            # =========================================================
            # Step 4: Retrieve memories
            # =========================================================
            print("\n🔍 Step 4: Retrieving memories...")

            try:
                memories = await client.retrieve(
                    query="What food does the user like?",
                    user_id=user_id,
                    agent_id=agent_id,
                )

                print(f"   Found {len(memories.items)} memory items")
                if memories.items:
                    for item in memories.items[:5]:
                        if hasattr(item, "memory_type"):
                            print(f"      - [{item.memory_type}] {item.summary[:60] if item.summary else ''}...")
                        elif isinstance(item, dict):
                            print(f"      - [{item.get('memory_type')}] {item.get('summary', '')[:60]}...")

                if memories.categories:
                    print(f"   Related categories: {len(memories.categories)}")
            except MemUClientError as e:
                print(f"   Note: {e.message}")

            print("\n✨ Demo completed!")

    except MemUAuthenticationError:
        print("❌ Authentication failed. Please check your API key.")
    except MemUClientError as e:
        print(f"❌ API error: {e.message}")
        if e.response:
            print(f"   Details: {e.response}")


async def main() -> None:
    """Run the demo."""
    await demo_cloud_api()

    print("\n" + "=" * 60)
    print("📖 For more information, see docs/SDK.md")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
