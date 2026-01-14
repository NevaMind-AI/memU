"""
Test OpenRouter integration with MemU's full workflow.

Tests:
1. Conversation memorization using OpenRouter
2. RAG-based retrieval using OpenRouter embeddings
3. LLM-based retrieval using OpenRouter

Usage:
    export OPENROUTER_API_KEY=your_api_key
    python tests/test_openrouter.py
"""

import asyncio
import json
import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from memu.app import MemoryService


def _print_categories(categories, max_items=3):
    """Print category summaries."""
    if categories:
        print("  Categories:")
        for cat in categories[:max_items]:
            summary = cat.get("summary") or cat.get("description", "")
            print(f"    - {cat.get('name')}: {summary[:60]}...")


def _print_items(items, max_items=3):
    """Print memory item summaries."""
    if items:
        print("  Items:")
        for item in items[:max_items]:
            memory_type = item.get("memory_type", "unknown")
            summary = item.get("summary", "")[:80]
            print(f"    - [{memory_type}] {summary}...")


async def _test_memorize(service, file_path, output_data):
    """Test conversation memorization."""
    print("\n[OPENROUTER] Test 1: Memorizing conversation...")
    memory = await service.memorize(
        resource_url=file_path, modality="conversation", user={"user_id": "openrouter_test_user"}
    )
    items_count = len(memory.get("items", []))
    categories_count = len(memory.get("categories", []))

    print(f"  Memorized {items_count} items")
    print(f"  Created {categories_count} categories")

    output_data["memorize"] = memory

    assert items_count > 0, "Expected at least 1 memory item"
    assert categories_count > 0, "Expected at least 1 category"

    _print_categories(memory.get("categories", []))
    return memory


async def _test_retrieve(service, queries, method, test_num, output_data):
    """Test retrieval with specified method."""
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
    return result


async def test_openrouter_full_workflow():
    """Test OpenRouter integration with full MemU workflow."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY environment variable not set")

    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "example", "example_conversation.json"))
    if not os.path.exists(file_path):
        pytest.skip(f"Test file not found: {file_path}")

    output_data: dict[str, Any] = {}

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

    queries = [
        {"role": "user", "content": {"text": "What foods does the user like to eat?"}},
    ]

    await _test_memorize(service, file_path, output_data)
    await _test_retrieve(service, queries, "rag", 2, output_data)
    await _test_retrieve(service, queries, "llm", 3, output_data)

    # Test 4: List memory items
    print("\n[OPENROUTER] Test 4: List memory items...")
    items_result = await service.list_memory_items(where={"user_id": "openrouter_test_user"})
    items_list = items_result.get("items", [])
    print(f"  Listed {len(items_list)} memory items")
    output_data["list_items"] = items_result
    assert len(items_list) > 0, "Expected at least 1 item in list"

    # Test 5: List memory categories
    print("\n[OPENROUTER] Test 5: List memory categories...")
    cats_result = await service.list_memory_categories(where={"user_id": "openrouter_test_user"})
    cats_list = cats_result.get("categories", [])
    print(f"  Listed {len(cats_list)} categories")
    output_data["list_categories"] = cats_result
    assert len(cats_list) > 0, "Expected at least 1 category in list"

    # Save output to file
    output_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "examples", "output", "openrouter_test_output.json")
    )
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, default=str)
    print(f"\n[OPENROUTER] Output saved to: {output_file}")

    print("\n" + "=" * 60)
    print("[OPENROUTER] All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_openrouter_full_workflow())
