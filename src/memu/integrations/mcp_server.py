"""FastMCP server exposing MemU as Model Context Protocol tools.

Run as a stdio server:

    python -m memu.integrations.mcp_server

The companion module `mcp_server_lowlevel` exposes the same tools through the
official `mcp` SDK directly for users who prefer it over FastMCP.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import uuid
from typing import TYPE_CHECKING

from memu.app.service import MemoryService

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("memu.integrations.mcp")


class _MemUTools:
    """Async tool implementations shared by both FastMCP and low-level servers."""

    def __init__(self, service: MemoryService):
        self.service = service

    async def memorize(self, content: str, user_id: str, modality: str = "conversation") -> str:
        path = os.path.join(tempfile.gettempdir(), f"memu_mcp_{uuid.uuid4()}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            await self.service.memorize(resource_url=path, modality=modality, user={"user_id": user_id})
        except Exception as e:
            logger.exception("memorize failed for user %s", user_id)
            return f"Failed to save memory: {e!s}"
        finally:
            with contextlib.suppress(OSError):
                os.unlink(path)
        return "Memory saved."

    async def retrieve(self, query: str, user_id: str, limit: int = 5) -> str:
        try:
            result = await self.service.retrieve(
                queries=[{"role": "user", "content": query}],
                where={"user_id": user_id},
            )
        except Exception as e:
            logger.exception("retrieve failed for user %s", user_id)
            return f"Failed to retrieve memory: {e!s}"
        items = (result.get("items") or [])[:limit]
        if not items:
            return "No relevant memories found."
        return "\n".join(f"- {it.get('summary', '')}" for it in items)

    async def list_items(self, user_id: str) -> str:
        result = await self.service.list_memory_items(where={"user_id": user_id})
        items = result.get("items") or []
        if not items:
            return "No memory items."
        return "\n".join(f"- [{it.get('memory_type')}] {it.get('summary', '')}" for it in items)

    async def list_categories(self, user_id: str) -> str:
        result = await self.service.list_memory_categories(where={"user_id": user_id})
        cats = result.get("categories") or []
        if not cats:
            return "No categories."
        return "\n".join(f"- {c.get('name')}: {c.get('summary') or c.get('description', '')}" for c in cats)

    async def clear_memory(self, user_id: str) -> str:
        await self.service.clear_memory(where={"user_id": user_id})
        return f"Cleared memory for user {user_id}."


def build_server(service: MemoryService) -> FastMCP:
    """Build a FastMCP server exposing the five MemU tools.

    Requires `pip install memu-py[mcp]` for the `fastmcp` dependency.
    """
    try:
        from fastmcp import FastMCP
    except ImportError as e:
        msg = "Install 'memu-py[mcp]' (which pulls in fastmcp) to use this integration."
        raise ImportError(msg) from e

    tools = _MemUTools(service)
    mcp = FastMCP("memu")

    @mcp.tool
    async def memu_memorize(content: str, user_id: str, modality: str = "conversation") -> str:
        """Save content to long-term memory for a user."""
        return await tools.memorize(content, user_id, modality)

    @mcp.tool
    async def memu_retrieve(query: str, user_id: str, limit: int = 5) -> str:
        """Search memories relevant to the query."""
        return await tools.retrieve(query, user_id, limit)

    @mcp.tool
    async def memu_list_items(user_id: str) -> str:
        """List all memory items for a user."""
        return await tools.list_items(user_id)

    @mcp.tool
    async def memu_list_categories(user_id: str) -> str:
        """List all memory categories with their summaries for a user."""
        return await tools.list_categories(user_id)

    @mcp.tool
    async def memu_clear_memory(user_id: str) -> str:
        """Delete every memory item, category, and resource for a user."""
        return await tools.clear_memory(user_id)

    return mcp


def _service_from_env() -> MemoryService:
    """Build a default MemoryService from environment variables.

    Reads ``MEMU_API_KEY`` (or ``OPENAI_API_KEY`` as a fallback) and, optionally,
    ``MEMU_BASE_URL`` / ``MEMU_CHAT_MODEL`` / ``MEMU_EMBED_MODEL`` so the CLI
    entry point works against any OpenAI-compatible provider (DeepSeek, Qwen
    DashScope, OpenRouter, Together, local Ollama, ...). Users who need
    separate chat and embedding endpoints should construct a MemoryService
    explicitly and pass it to :func:`build_server`.
    """
    api_key = os.environ.get("MEMU_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "Set MEMU_API_KEY (or OPENAI_API_KEY) before launching the MCP server."
        raise RuntimeError(msg)
    profile: dict[str, str] = {"api_key": api_key}
    for env, key in (
        ("MEMU_BASE_URL", "base_url"),
        ("MEMU_CHAT_MODEL", "chat_model"),
        ("MEMU_EMBED_MODEL", "embed_model"),
    ):
        if value := os.environ.get(env):
            profile[key] = value
    return MemoryService(llm_profiles={"default": profile})


def main() -> None:
    """Entry point for ``python -m memu.integrations.mcp_server``."""
    build_server(_service_from_env()).run()


if __name__ == "__main__":
    main()
