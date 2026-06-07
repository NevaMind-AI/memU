"""Register MemU as a Model Context Protocol server with Claude Code.

Two integrations are shipped: a FastMCP-based one (recommended) and a
low-level one using the official `mcp` SDK directly. Both expose the same
five tools (memorize, retrieve, list_items, list_categories, clear_memory).

Install one of the optional extras and register the server::

    # FastMCP (recommended)
    pip install "memu-py[mcp]"
    claude mcp add memu -- python -m memu.integrations.mcp_server

    # Low-level (official `mcp` SDK)
    pip install "memu-py[mcp-lowlevel]"
    claude mcp add memu -- python -m memu.integrations.mcp_server_lowlevel

The default CLI entry reads ``MEMU_API_KEY`` (or ``OPENAI_API_KEY``) and the
optional overrides ``MEMU_BASE_URL`` / ``MEMU_CHAT_MODEL`` /
``MEMU_EMBED_MODEL``, so it works against any OpenAI-compatible provider
(DeepSeek, Qwen DashScope, OpenRouter, Together, local Ollama, ...). For
separate chat and embedding endpoints, or a non-default storage backend,
construct the service programmatically as shown below.
"""

from __future__ import annotations

import os

from memu.app.service import MemoryService
from memu.integrations.mcp_server import build_server


def main() -> None:
    service = MemoryService(
        llm_profiles={"default": {"api_key": os.environ["OPENAI_API_KEY"]}},
        database_config={"metadata_store": {"provider": "inmemory"}},
    )
    build_server(service).run()


if __name__ == "__main__":
    main()
