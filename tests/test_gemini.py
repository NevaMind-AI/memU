import os

import pytest

from memu.app import MemoryService


@pytest.mark.asyncio
async def test_gemini_flow():
    """Test with Gemini provider."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")

    # Use relative path from project root or find file appropriately
    base_dir = os.path.dirname(os.path.dirname(__file__))
    file_path = os.path.join(base_dir, "example", "example_conversation.json")
    if not os.path.exists(file_path):
        file_path = os.path.abspath("example/example_conversation.json")

    print("\n" + "=" * 60)
    print("[GEMINI] Starting test...")
    print("=" * 60)

    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "gemini",
                "api_key": api_key,
                # Defaults in logic should handle model names if not specified,
                # but let's be explicit to test config passing or rely on defaults to test those.
                # Let's rely on defaults we set in service.py
            }
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
        retrieve_config={"method": "rag"},
    )

    # Memorize
    print("\n[GEMINI] Memorizing...")
    try:
        memory = await service.memorize(
            resource_url=file_path, modality="conversation", user={"user_id": "test_gemini"}
        )
        assert memory is not None
        for cat in memory.get("categories", []):
            print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")
    except Exception as e:
        pytest.fail(f"Memorization failed: {e}")

    queries = [
        {"role": "user", "content": {"text": "Tell me about preferences"}},
        {"role": "assistant", "content": {"text": "Sure, I'll tell you about their preferences"}},
        {
            "role": "user",
            "content": {"text": "What are they"},
        },
    ]

    # RAG-based retrieval
    print("\n[GEMINI] RETRIEVED - RAG")
    service.retrieve_config.method = "rag"
    result_rag = await service.retrieve(queries=queries, where={"user_id": "test_gemini"})
    assert result_rag is not None
    print("  Categories:")
    for cat in result_rag.get("categories", [])[:3]:
        print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:80]}...")
    print("  Items:")
    for item in result_rag.get("items", [])[:3]:
        print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")

    # LLM-based retrieval (delegated to Gemini)
    print("\n[GEMINI] RETRIEVED - LLM")
    service.retrieve_config.method = "llm"
    result_llm = await service.retrieve(queries=queries, where={"user_id": "test_gemini"})
    assert result_llm is not None
    print("  Categories:")
    for cat in result_llm.get("categories", [])[:3]:
        print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:80]}...")

    print("\n[GEMINI] Test completed!")
