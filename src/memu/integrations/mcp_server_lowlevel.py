"""Low-level MCP server using the official `mcp` SDK directly.

Exposes the same five tools as :mod:`memu.integrations.mcp_server` but binds
them via :class:`mcp.server.lowlevel.Server`. Useful for users who prefer the
official protocol library over FastMCP. Run as a stdio server:

    python -m memu.integrations.mcp_server_lowlevel
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from memu.app.service import MemoryService
from memu.integrations.mcp_server import _MemUTools, _service_from_env

if TYPE_CHECKING:
    from mcp.server.lowlevel import Server

_TOOL_SCHEMA: dict[str, dict[str, Any]] = {
    "memu_memorize": {
        "description": "Save content to long-term memory for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "user_id": {"type": "string"},
                "modality": {"type": "string", "default": "conversation"},
            },
            "required": ["content", "user_id"],
        },
    },
    "memu_retrieve": {
        "description": "Search memories relevant to the query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "user_id": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query", "user_id"],
        },
    },
    "memu_list_items": {
        "description": "List all memory items for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    "memu_list_categories": {
        "description": "List all memory categories with their summaries for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    "memu_clear_memory": {
        "description": "Delete every memory item, category, and resource for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
}


def build_server(service: MemoryService) -> Server:
    """Build a low-level MCP Server exposing the same five tools as `mcp_server`.

    Requires `pip install memu-py[mcp-lowlevel]` for the `mcp` dependency.
    """
    try:
        import mcp.types as types
        from mcp.server.lowlevel import Server
    except ImportError as e:
        msg = "Install 'memu-py[mcp-lowlevel]' (which pulls in mcp) to use this integration."
        raise ImportError(msg) from e

    tools = _MemUTools(service)
    server = Server("memu")
    handlers: dict[str, Callable[..., Awaitable[str]]] = {
        "memu_memorize": tools.memorize,
        "memu_retrieve": tools.retrieve,
        "memu_list_items": tools.list_items,
        "memu_list_categories": tools.list_categories,
        "memu_clear_memory": tools.clear_memory,
    }

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [types.Tool(name=name, **schema) for name, schema in _TOOL_SCHEMA.items()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        handler = handlers.get(name)
        if handler is None:
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)
        result = await handler(**arguments)
        return [types.TextContent(type="text", text=result)]

    return server


async def _run(service: MemoryService) -> None:
    import mcp.server.stdio
    from mcp.server.lowlevel import NotificationOptions
    from mcp.server.models import InitializationOptions

    server = build_server(service)
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="memu",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """Entry point for ``python -m memu.integrations.mcp_server_lowlevel``."""
    asyncio.run(_run(_service_from_env()))


if __name__ == "__main__":
    main()
