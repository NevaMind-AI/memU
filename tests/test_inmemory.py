#!/usr/bin/env python3
"""Opt-in live LLM smoke test for the in-memory backend."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_LIVE_LLM_TESTS_ENV = "MEMU_RUN_LIVE_LLM_TESTS"

# Add src to sys.path before importing memu from a source checkout.
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


async def run_inmemory_workflow() -> None:
    """Run the in-memory memorize/retrieve smoke workflow against a real LLM."""
    from memu import MemoryService

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY is required for the in-memory live LLM workflow"
        raise RuntimeError(msg)

    file_path = Path(__file__).resolve().parent / "example" / "example_conversation.json"

    print("\n" + "=" * 60)
    print("[INMEMORY] Starting test...")
    print("=" * 60)

    service = MemoryService(
        llm_profiles={"default": {"api_key": api_key}},
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
        retrieve_config={"method": "rag"},
    )

    print("\n[INMEMORY] Memorizing...")
    memory = await service.memorize(resource_url=str(file_path), modality="conversation", user={"user_id": "123"})
    for cat in memory.get("categories", []):
        print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")

    queries = _sample_queries()

    print("\n[INMEMORY] RETRIEVED - RAG")
    service.retrieve_config.method = "rag"
    result_rag = await service.retrieve(queries=queries, where={"user_id": "123"})
    _print_results(result_rag)

    print("\n[INMEMORY] RETRIEVED - LLM")
    service.retrieve_config.method = "llm"
    result_llm = await service.retrieve(queries=queries, where={"user_id": "123"})
    _print_results(result_llm)

    print("\n[INMEMORY] Test completed!")


async def test_inmemory_full_workflow() -> None:
    """Opt-in pytest integration check for the in-memory backend and a real LLM."""
    import pytest

    if os.environ.get(RUN_LIVE_LLM_TESTS_ENV) != "1":
        pytest.skip(f"Set {RUN_LIVE_LLM_TESTS_ENV}=1 to run live LLM storage workflows")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live LLM storage workflows")

    await run_inmemory_workflow()


def _sample_queries() -> list[dict[str, dict[str, str] | str]]:
    return [
        {"role": "user", "content": {"text": "Tell me about preferences"}},
        {"role": "assistant", "content": {"text": "Sure, I'll tell you about their preferences"}},
        {"role": "user", "content": {"text": "What are they"}},
    ]


def _print_results(result: dict[str, Any]) -> None:
    print("  Categories:")
    for cat in result.get("categories", [])[:3]:
        print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:80]}...")
    print("  Items:")
    for item in result.get("items", [])[:3]:
        print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")
    if result.get("resources"):
        print("  Resources:")
        for res in result.get("resources", [])[:3]:
            print(f"    - [{res.get('modality')}] {res.get('url', '')[:80]}...")


def main() -> int:
    asyncio.run(run_inmemory_workflow())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
