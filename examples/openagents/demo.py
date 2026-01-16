"""
MemU + OpenAgents Integration Demo

This script demonstrates how to use MemU's long-term memory
with OpenAgents agents.

Requirements:
    pip install memu openagents

Usage:
    python demo.py
"""

import asyncio
import os

# MemU imports
from memu.app.service import MemoryService
from memu.adapters.openagents import MemUOpenAgentsAdapter, get_memu_tools


async def demo_standalone_tools():
    """Demo: Using MemU tools standalone (without full OpenAgents network)."""
    print("\n" + "=" * 60)
    print("Demo 1: Standalone MemU Tools")
    print("=" * 60)

    # Initialize MemU service with in-memory storage
    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "chat_model": "gpt-4o-mini",
            },
            "embedding": {
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "embed_model": "text-embedding-3-small",
            },
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
    )

    # Create adapter
    adapter = MemUOpenAgentsAdapter(service=service)
    adapter.initialize(agent_id="demo-agent")

    # Demo: Memorize some information
    print("\n📝 Storing memories...")

    result = await adapter.call_tool(
        "memorize",
        content="John is a senior backend engineer who specializes in Python and PostgreSQL. "
        "He has 8 years of experience and leads the database optimization team.",
    )
    print(f"  {result}")

    result = await adapter.call_tool(
        "memorize",
        content="Sarah is a frontend developer expert in React and TypeScript. "
        "She joined the team 2 years ago and focuses on accessibility.",
    )
    print(f"  {result}")

    result = await adapter.call_tool(
        "memorize",
        content="The project deadline is March 15th. We need to complete the API "
        "refactoring and deploy to staging by March 10th.",
    )
    print(f"  {result}")

    # Demo: List memories
    print("\n📚 Listing stored memories...")
    result = await adapter.call_tool("list_memories", limit=5)
    print(f"  {result}")

    # Demo: Retrieve relevant memories
    print("\n🔍 Querying: 'Who can help with database performance?'")
    result = await adapter.call_tool(
        "retrieve",
        query="Who can help with database performance?",
        top_k=3,
    )
    print(f"  {result}")

    print("\n🔍 Querying: 'What are the upcoming deadlines?'")
    result = await adapter.call_tool(
        "retrieve",
        query="What are the upcoming deadlines?",
        top_k=3,
    )
    print(f"  {result}")

    print("\n✅ Standalone demo complete!")


async def demo_with_openagents():
    """Demo: Using MemU with OpenAgents (requires running network)."""
    print("\n" + "=" * 60)
    print("Demo 2: MemU with OpenAgents Network")
    print("=" * 60)

    try:
        from openagents import Agent
    except ImportError:
        print("⚠️  OpenAgents not installed. Skipping network demo.")
        print("   Install with: pip install openagents")
        return

    # Initialize MemU service
    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "chat_model": "gpt-4o-mini",
            },
            "embedding": {
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "embed_model": "text-embedding-3-small",
            },
        },
        database_config={
            "metadata_store": {"provider": "sqlite", "path": "memory.db"},
        },
    )

    # Create adapter
    adapter = MemUOpenAgentsAdapter(service=service)

    # Get tools for agent registration
    tools = adapter.get_tools()
    print(f"\n📦 Available MemU tools: {[t['name'] for t in tools]}")

    # Get YAML-compatible schemas
    schemas = adapter.get_tool_schemas()
    print(f"📄 Tool schemas for YAML config: {len(schemas)} tools")

    print("\n✅ OpenAgents integration ready!")
    print("   Use the memory_agent.yaml config to run an agent with memory.")


async def main():
    """Run all demos."""
    print("🧠 MemU + OpenAgents Integration Demo")
    print("=" * 60)

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Using mock mode.")
        print("   Set your API key to run the full demo.")
        return

    await demo_standalone_tools()
    await demo_with_openagents()

    print("\n" + "=" * 60)
    print("🎉 All demos complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
