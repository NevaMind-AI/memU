"""Minimal end-to-end example: memU backed by a Milvus vector index.

Uses the ``inmemory`` metadata store and Milvus Lite (a single ``milvus.db``
file) so it runs with zero external services. Point ``uri`` at a Milvus server
URL or a Zilliz Cloud endpoint to scale to production.

Run:

    uv sync --extra milvus
    export OPENAI_API_KEY=sk-...
    uv run python examples/milvus_vector_index.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from memu.app import MemoryService


async def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "Set OPENAI_API_KEY before running this example."
        raise SystemExit(msg)

    file_path = os.path.abspath("example/example_conversation.json")
    if not Path(file_path).exists():
        msg = (
            f"Example conversation not found at {file_path}. "
            "Run from the repository root so the 'example/' folder is visible."
        )
        raise SystemExit(msg)

    service = MemoryService(
        llm_profiles={"default": {"api_key": api_key}},
        database_config={
            "metadata_store": {"provider": "inmemory"},
            "vector_index": {
                "provider": "milvus",
                # Local Milvus Lite file. Swap for "http://host:19530" or a
                # Zilliz Cloud endpoint to target a real deployment.
                "uri": "./milvus.db",
                "collection_name": "memu_example",
            },
        },
        retrieve_config={"method": "rag"},
    )

    print("[memU + Milvus] Memorizing example conversation...")
    memory = await service.memorize(
        resource_url=file_path,
        modality="conversation",
        user={"user_id": "demo-user"},
    )
    for cat in memory.get("categories", []):
        print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")

    queries = [
        {"role": "user", "content": {"text": "What do you know about my preferences?"}},
    ]
    result = await service.retrieve(queries=queries, where={"user_id": "demo-user"})

    print("\n[memU + Milvus] Retrieved items:")
    for item in result.get("items", [])[:5]:
        print(f"  - [{item.get('memory_type')}] {(item.get('summary') or '')[:100]}")


if __name__ == "__main__":
    asyncio.run(main())
