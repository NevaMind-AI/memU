"""
MemU Tools for OpenAgents - Standalone tool functions.

These tools can be used directly with the @tool decorator pattern
or registered in agent YAML configs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.service import MemoryService

logger = logging.getLogger(__name__)

# Global service reference (set by adapter or manually)
_memu_service: MemoryService | None = None


def set_memu_service(service: MemoryService) -> None:
    """Set the global MemU service instance for tools to use."""
    global _memu_service
    _memu_service = service


def get_memu_service() -> MemoryService:
    """Get the global MemU service instance."""
    if _memu_service is None:
        msg = "MemU service not initialized. Call set_memu_service() first."
        raise RuntimeError(msg)
    return _memu_service


def _run_async(coro: Any) -> Any:
    """Run async coroutine from sync context."""
    try:
        asyncio.get_running_loop()
        # If we're in an async context, run in executor
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=60)
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(coro)


def memorize(
    content: str,
    modality: str = "text",
    user_id: str | None = None,
) -> str:
    """
    Store a memory in MemU.

    Args:
        content: The text content to memorize
        modality: Type of content - "text", "conversation", "document" (default: "text")
        user_id: Optional user ID for scoping memories

    Returns:
        Status message with stored memory details
    """
    try:
        service = get_memu_service()

        # Create a temporary file-like resource URL for text content
        import hashlib
        import os
        import tempfile

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
        temp_path = os.path.join(tempfile.gettempdir(), f"memu_{content_hash}.txt")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)

        user_scope = {"user_id": user_id} if user_id else None

        result = _run_async(
            service.memorize(
                resource_url=temp_path,
                modality=modality,
                user=user_scope,
            )
        )

        # Clean up temp file
        import contextlib

        with contextlib.suppress(OSError):
            os.remove(temp_path)

    except Exception as e:
        logger.exception("memorize failed")
        return f"❌ Failed to memorize: {e!s}"

    items = result.get("items", [])
    item_count = len(items)

    if item_count == 0:
        return "⚠️ No memories extracted from content."

    summaries = [item.get("summary", "")[:100] for item in items[:3]]
    preview = "\n".join(f"  • {s}..." if len(s) == 100 else f"  • {s}" for s in summaries)

    return f"✅ Stored {item_count} memory item(s):\n{preview}"


def retrieve(
    query: str,
    top_k: int = 5,
    user_id: str | None = None,
) -> str:
    """
    Query memories from MemU using semantic search.

    Args:
        query: Natural language query to search memories
        top_k: Maximum number of results to return (default: 5)
        user_id: Optional user ID to scope the search

    Returns:
        Retrieved memories formatted as text
    """
    try:
        service = get_memu_service()

        queries = [{"text": query, "role": "user"}]
        where = {"user_id": user_id} if user_id else None

        result = _run_async(service.retrieve(queries=queries, where=where))

        if not result.get("needs_retrieval", True):
            return "No retrieval needed for this query."

        items = result.get("items", [])
        categories = result.get("categories", [])

        if not items and not categories:
            return "📭 No relevant memories found."

        output_parts = []

        if categories:
            output_parts.append("📁 **Relevant Categories:**")
            for cat in categories[:3]:
                name = cat.get("name", "Unknown")
                summary = cat.get("summary", "")[:150]
                output_parts.append(f"  • {name}: {summary}")

        if items:
            output_parts.append(f"\n📝 **Retrieved Memories ({len(items)}):**")
            for i, item in enumerate(items[:top_k], 1):
                summary = item.get("summary", "No summary")
                mem_type = item.get("memory_type", "unknown")
                score = item.get("score", 0)
                output_parts.append(f"  {i}. [{mem_type}] {summary}")
                if score:
                    output_parts[-1] += f" (score: {score:.2f})"

        return "\n".join(output_parts)

    except Exception as e:
        logger.exception("retrieve failed")
        return f"❌ Failed to retrieve: {e!s}"


def list_memories(
    limit: int = 10,
    memory_type: str | None = None,
    user_id: str | None = None,
) -> str:
    """
    List stored memory items.

    Args:
        limit: Maximum number of items to return (default: 10)
        memory_type: Filter by memory type (e.g., "knowledge", "event", "preference")
        user_id: Optional user ID to scope the list

    Returns:
        Formatted list of memory items
    """
    try:
        service = get_memu_service()

        where = {}
        if user_id:
            where["user_id"] = user_id
        if memory_type:
            where["memory_type"] = memory_type

        result = _run_async(service.list_memory_items(where=where if where else None))

        items = result.get("items", [])

        if not items:
            return "📭 No memories stored yet."

        items = items[:limit]
        output_parts = [f"📚 **Stored Memories ({len(items)}):**\n"]

        for item in items:
            item_id = item.get("id", "?")[:8]
            summary = item.get("summary", "No summary")[:80]
            mem_type = item.get("memory_type", "unknown")
            output_parts.append(f"  • [{item_id}] ({mem_type}) {summary}")

        return "\n".join(output_parts)

    except Exception as e:
        logger.exception("list_memories failed")
        return f"❌ Failed to list memories: {e!s}"


def get_memory(memory_id: str) -> str:
    """
    Get a specific memory item by ID.

    Args:
        memory_id: The ID of the memory item to retrieve

    Returns:
        Full memory item details
    """
    try:
        service = get_memu_service()

        result = _run_async(service.get_memory_item(item_id=memory_id))

        if not result or not result.get("item"):
            return f"📭 Memory '{memory_id}' not found."

        item = result["item"]
        output_parts = [
            f"📝 **Memory: {item.get('id', memory_id)}**\n",
            f"**Type:** {item.get('memory_type', 'unknown')}",
            f"**Summary:** {item.get('summary', 'No summary')}",
            f"**Created:** {item.get('created_at', 'Unknown')}",
        ]

        if item.get("resource_id"):
            output_parts.append(f"**Resource:** {item['resource_id']}")

        return "\n".join(output_parts)

    except Exception as e:
        logger.exception("get_memory failed")
        return f"❌ Failed to get memory: {e!s}"


# Tool schemas for OpenAgents YAML config
TOOL_SCHEMAS = {
    "memorize": {
        "name": "memorize",
        "description": "Store a memory in MemU long-term memory system",
        "implementation": "memu.adapters.openagents.tools.memorize",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The text content to memorize",
                },
                "modality": {
                    "type": "string",
                    "description": "Type of content: text, conversation, document",
                    "default": "text",
                },
                "user_id": {
                    "type": "string",
                    "description": "Optional user ID for scoping memories",
                },
            },
            "required": ["content"],
        },
    },
    "retrieve": {
        "name": "retrieve",
        "description": "Query memories from MemU using semantic search",
        "implementation": "memu.adapters.openagents.tools.retrieve",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search memories",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
                "user_id": {
                    "type": "string",
                    "description": "Optional user ID to scope the search",
                },
            },
            "required": ["query"],
        },
    },
    "list_memories": {
        "name": "list_memories",
        "description": "List stored memory items in MemU",
        "implementation": "memu.adapters.openagents.tools.list_memories",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum items to return (default: 10)",
                    "default": 10,
                },
                "memory_type": {
                    "type": "string",
                    "description": "Filter by type: knowledge, event, preference",
                },
                "user_id": {
                    "type": "string",
                    "description": "Optional user ID to scope the list",
                },
            },
            "required": [],
        },
    },
    "get_memory": {
        "name": "get_memory",
        "description": "Get a specific memory item by ID",
        "implementation": "memu.adapters.openagents.tools.get_memory",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "The ID of the memory item to retrieve",
                },
            },
            "required": ["memory_id"],
        },
    },
}


def get_memu_tools(service: MemoryService | None = None) -> list[dict[str, Any]]:
    """
    Get MemU tools configured for OpenAgents.

    Args:
        service: Optional MemoryService instance. If provided, sets the global service.

    Returns:
        List of tool configurations for OpenAgents YAML config
    """
    if service is not None:
        set_memu_service(service)

    return list(TOOL_SCHEMAS.values())
