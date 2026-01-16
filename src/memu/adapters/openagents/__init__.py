"""
MemU OpenAgents Adapter - Long-term memory for OpenAgents networks.

This adapter provides memory tools that any OpenAgents agent can use:
- memorize: Store memories from text, conversations, documents
- retrieve: Query memories with semantic search
- list_memories: List stored memory items
- get_memory: Get a specific memory by ID

Usage:
    from memu.adapters.openagents import MemUOpenAgentsAdapter, get_memu_tools

    # Option 1: Use adapter class (recommended for agent integration)
    adapter = MemUOpenAgentsAdapter(service=memu_service)
    tools = adapter.get_tools()

    # Option 2: Get tools directly (for YAML config)
    tools = get_memu_tools(service=memu_service)
"""

from memu.adapters.openagents.adapter import MemUOpenAgentsAdapter
from memu.adapters.openagents.tools import get_memu_tools

__all__ = ["MemUOpenAgentsAdapter", "get_memu_tools"]
