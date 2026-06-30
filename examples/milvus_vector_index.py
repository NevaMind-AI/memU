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

from memu.app import MemoryService


async def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "Set OPENAI_API_KEY before running this example."
        raise SystemExit(msg)

    service = MemoryService(
        embedding_profiles={"default": {"api_key": api_key}},
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
    )

    print("[memU + Milvus] Committing recall files...")
    await service.commit_results(
        recall_files=[
            {
                "name": "Profile",
                "track": "memory",
                "description": "user preferences",
                "content": "# Profile\nprefers espresso\nships releases on Fridays",
            },
            {
                "name": "release-checklist",
                "track": "skill",
                "description": "release steps",
                "content": "run tests\nbuild package\npush tag",
            },
        ],
        resource=[{"path": os.path.abspath("README.md"), "description": "project overview and usage notes"}],
        user={"user_id": "demo-user"},
    )

    result = await service.progressive_retrieve("What does the user prefer?", where={"user_id": "demo-user"})

    print("\n[memU + Milvus] Retrieved segments:")
    for segment in result.get("segments", [])[:5]:
        print(f"  - [{segment.get('track')}] {segment.get('text')} (score={segment.get('score'):.3f})")

    print("\n[memU + Milvus] Retrieved files:")
    for file in result.get("files", [])[:5]:
        print(f"  - [{file.get('track')}] {file.get('name')}")


if __name__ == "__main__":
    asyncio.run(main())
