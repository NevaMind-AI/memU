#!/usr/bin/env python3
"""
Opt-in OpenRouter integration smoke test.

Usage:
    export OPENROUTER_API_KEY=your_api_key
    export MEMU_RUN_OPENROUTER_TESTS=1
    uv run python -m pytest tests/test_openrouter.py

Manual run:
    export OPENROUTER_API_KEY=your_api_key
    python tests/test_openrouter.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_OPENROUTER_TESTS_ENV = "MEMU_RUN_OPENROUTER_TESTS"

# Add src to sys.path before importing memu from a source checkout.
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


async def run_openrouter_workflow() -> None:
    """Run the OpenRouter-backed memorize/retrieve smoke workflow."""
    from memu import MemoryService

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        msg = "OPENROUTER_API_KEY is required for the OpenRouter integration workflow"
        raise RuntimeError(msg)

    file_path = Path(__file__).resolve().parent / "example" / "example_conversation.json"

    print("\n" + "=" * 60)
    print("[OPENROUTER] Starting full workflow test...")
    print("=" * 60)

    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "openrouter",
                "client_backend": "httpx",
                "base_url": "https://openrouter.ai",
                "api_key": api_key,
                "chat_model": "anthropic/claude-3.5-sonnet",
                "embed_model": "openai/text-embedding-3-small",
            },
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
        retrieve_config={
            "method": "rag",
            "route_intention": False,
        },
    )

    output_data: dict[str, Any] = {}
    queries = [
        {"role": "user", "content": {"text": "What foods does the user like to eat?"}},
    ]

    await _test_memorize(service, str(file_path), output_data)
    await _test_retrieve(service, queries, "rag", 2, output_data)
    await _test_retrieve(service, queries, "llm", 3, output_data)

    print("\n[OPENROUTER] Test 4: List memory items...")
    items_result = await service.list_memory_items(where={"user_id": "openrouter_test_user"})
    items_list = items_result.get("items", [])
    print(f"  Listed {len(items_list)} memory items")
    output_data["list_items"] = items_result
    assert len(items_list) > 0, "Expected at least 1 item in list"

    print("\n[OPENROUTER] Test 5: List memory categories...")
    cats_result = await service.list_memory_categories(where={"user_id": "openrouter_test_user"})
    cats_list = cats_result.get("categories", [])
    print(f"  Listed {len(cats_list)} categories")
    output_data["list_categories"] = cats_result
    assert len(cats_list) > 0, "Expected at least 1 category in list"

    print("\n" + "=" * 60)
    print("[OPENROUTER] All tests completed!")
    print("=" * 60)


async def test_openrouter_full_workflow() -> None:
    """Opt-in pytest integration check for OpenRouter-backed model calls."""
    import pytest

    if os.environ.get(RUN_OPENROUTER_TESTS_ENV) != "1":
        pytest.skip(f"Set {RUN_OPENROUTER_TESTS_ENV}=1 to run the OpenRouter integration workflow")
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY is required for the OpenRouter integration workflow")

    await run_openrouter_workflow()


async def _test_memorize(service: Any, file_path: str, output_data: dict[str, Any]) -> None:
    print("\n[OPENROUTER] Test 1: Memorizing conversation...")
    memory = await service.memorize(
        resource_url=file_path,
        modality="conversation",
        user={"user_id": "openrouter_test_user"},
    )
    items_count = len(memory.get("items", []))
    categories_count = len(memory.get("categories", []))

    print(f"  Memorized {items_count} items")
    print(f"  Created {categories_count} categories")

    output_data["memorize"] = memory

    assert items_count > 0, "Expected at least 1 memory item"
    assert categories_count > 0, "Expected at least 1 category"

    _print_categories(memory.get("categories", []))


async def _test_retrieve(
    service: Any,
    queries: list[dict[str, Any]],
    method: str,
    test_num: int,
    output_data: dict[str, Any],
) -> None:
    print(f"\n[OPENROUTER] Test {test_num}: {method.upper()}-based retrieval...")
    service.retrieve_config.method = method
    result = await service.retrieve(queries=queries, where={"user_id": "openrouter_test_user"})

    categories_retrieved = len(result.get("categories", []))
    items_retrieved = len(result.get("items", []))

    print(f"  Retrieved {categories_retrieved} categories")
    print(f"  Retrieved {items_retrieved} items")

    output_data[f"retrieve_{method}"] = result

    _print_categories(result.get("categories", []))
    _print_items(result.get("items", []))


def _print_categories(categories: list[dict[str, Any]], max_items: int = 3) -> None:
    if not categories:
        return
    print("  Categories:")
    for cat in categories[:max_items]:
        summary = cat.get("summary") or cat.get("description", "")
        print(f"    - {cat.get('name')}: {summary[:60]}...")


def _print_items(items: list[dict[str, Any]], max_items: int = 3) -> None:
    if not items:
        return
    print("  Items:")
    for item in items[:max_items]:
        memory_type = item.get("memory_type", "unknown")
        summary = item.get("summary", "")[:80]
        print(f"    - [{memory_type}] {summary}...")


def main() -> int:
    asyncio.run(run_openrouter_workflow())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
