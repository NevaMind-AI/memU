"""
Test Gemini integration with MemU's full workflow.

Tests:
1. Conversation memorization using Gemini
2. RAG-based retrieval using Gemini embeddings
3. LLM-based retrieval using Gemini

Usage:
    export GEMINI_API_KEY=your_api_key
    python tests/test_gemini.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from memu.app import MemoryService


async def test_gemini_full_workflow():
    """Test Gemini integration with full MemU workflow."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        print("Please set it with: export GEMINI_API_KEY=your_api_key")
        sys.exit(1)

    # Use minimal conversation for free-tier rate limit friendly testing
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "example", "example_conversation_minimal.json"))
    if not os.path.exists(file_path):
        print(f"ERROR: Test file not found: {file_path}")
        sys.exit(1)

    output_data = {}

    print("\n" + "=" * 60)
    print("[GEMINI] Starting full workflow test...")
    print("=" * 60)

    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "gemini",
                "client_backend": "httpx",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": api_key,
                "chat_model": "gemini-2.5-flash",
                "embed_model": "text-embedding-004",
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

    # Test 1: Memorize conversation
    print("\n[GEMINI] Test 1: Memorizing conversation...")
    memory = await service.memorize(
        resource_url=file_path,
        modality="conversation",
        user={"user_id": "gemini_test_user"}
    )
    items_count = len(memory.get("items", []))
    categories_count = len(memory.get("categories", []))
    
    print(f"  Memorized {items_count} items")
    print(f"  Created {categories_count} categories")
    
    output_data["memorize"] = memory
    
    assert items_count > 0, "Expected at least 1 memory item"
    assert categories_count > 0, "Expected at least 1 category"
    
    for cat in memory.get("categories", [])[:3]:
        print(f"    - {cat.get('name')}: {(cat.get('summary') or '')[:60]}...")

    queries = [
        {"role": "user", "content": {"text": "What foods does the user like to eat?"}},
    ]

    # Test 2: RAG-based retrieval
    print("\n[GEMINI] Test 2: RAG-based retrieval...")
    service.retrieve_config.method = "rag"
    result_rag = await service.retrieve(queries=queries, where={"user_id": "gemini_test_user"})
    
    categories_retrieved = len(result_rag.get("categories", []))
    items_retrieved = len(result_rag.get("items", []))
    
    print(f"  Retrieved {categories_retrieved} categories")
    print(f"  Retrieved {items_retrieved} items")
    
    output_data["retrieve_rag"] = result_rag
    
    if categories_retrieved > 0:
        print("  Categories:")
        for cat in result_rag.get("categories", [])[:3]:
            print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:60]}...")
    
    if items_retrieved > 0:
        print("  Items:")
        for item in result_rag.get("items", [])[:3]:
            print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:80]}...")

    # Test 3: LLM-based retrieval
    print("\n[GEMINI] Test 3: LLM-based retrieval...")
    service.retrieve_config.method = "llm"
    result_llm = await service.retrieve(queries=queries, where={"user_id": "gemini_test_user"})
    
    categories_retrieved = len(result_llm.get("categories", []))
    items_retrieved = len(result_llm.get("items", []))
    
    print(f"  Retrieved {categories_retrieved} categories")
    print(f"  Retrieved {items_retrieved} items")
    
    output_data["retrieve_llm"] = result_llm
    
    if categories_retrieved > 0:
        print("  Categories:")
        for cat in result_llm.get("categories", [])[:3]:
            print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:60]}...")
    
    if items_retrieved > 0:
        print("  Items:")
        for item in result_llm.get("items", [])[:3]:
            print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:80]}...")

    # Test 4: List memory items
    print("\n[GEMINI] Test 4: List memory items...")
    items_result = await service.list_memory_items(where={"user_id": "gemini_test_user"})
    items_list = items_result.get("items", [])
    print(f"  Listed {len(items_list)} memory items")
    output_data["list_items"] = items_result
    assert len(items_list) > 0, "Expected at least 1 item in list"

    # Test 5: List memory categories
    print("\n[GEMINI] Test 5: List memory categories...")
    cats_result = await service.list_memory_categories(where={"user_id": "gemini_test_user"})
    cats_list = cats_result.get("categories", [])
    print(f"  Listed {len(cats_list)} categories")
    output_data["list_categories"] = cats_result
    assert len(cats_list) > 0, "Expected at least 1 category in list"

    # Save output to file
    output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples", "output", "gemini_test_output.json"))
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, default=str)
    print(f"\n[GEMINI] Output saved to: {output_file}")

    print("\n" + "=" * 60)
    print("[GEMINI] All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_gemini_full_workflow())
