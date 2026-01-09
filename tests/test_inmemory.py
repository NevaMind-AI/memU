import os

from memu.app import MemoryService


async def main():
    """Test with in-memory storage (default)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    # dashscope_api_key = os.environ.get("DASHSCOPE_API_KEY")
    # voyage_api_key = os.environ.get("VOYAGE_API_KEY")
    file_path = os.path.abspath("example/example_conversation.json")

    print("\n" + "=" * 60)
    print("[INMEMORY] Starting test...")
    print("=" * 60)

    service = MemoryService(
        llm_profiles={"default": {"api_key": api_key}},
        # llm_profiles={
        #     "default": {
        #         "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        #         "api_key": dashscope_api_key,
        #         "chat_model": "qwen3-max",
        #         "client_backend": "sdk"
        #     },
        #     "embedding": {
        #         "base_url": "https://api.voyageai.com/v1",
        #         "api_key": voyage_api_key,
        #         "embed_model": "voyage-3.5-lite"
        #     }
        # },
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
        retrieve_config={"method": "rag"},
    )

    # Memorize
    print("\n[INMEMORY] Memorizing...")
    memory = await service.memorize(resource_url=file_path, modality="conversation", user={"user_id": "123"})
    for cat in memory.get("categories", []):
        print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")

    queries = [
        {"role": "user", "content": {"text": "Tell me about preferences"}},
        {"role": "assistant", "content": {"text": "Sure, I'll tell you about their preferences"}},
        {
            "role": "user",
            "content": {"text": "What are they"},
        },  # This is the query that will be used to retrieve the memory, the context will be used for query rewriting
    ]

    # RAG-based retrieval
    print("\n[INMEMORY] RETRIEVED - RAG")
    service.retrieve_config.method = "rag"
    result_rag = await service.retrieve(queries=queries, where={"user_id": "123"})
    print("  Categories:")
    for cat in result_rag.get("categories", [])[:3]:
        print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:80]}...")
    print("  Items:")
    for item in result_rag.get("items", [])[:3]:
        print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")
    if result_rag.get("resources"):
        print("  Resources:")
        for res in result_rag.get("resources", [])[:3]:
            print(f"    - [{res.get('modality')}] {res.get('url', '')[:80]}...")

    # LLM-based retrieval
    print("\n[INMEMORY] RETRIEVED - LLM")
    service.retrieve_config.method = "llm"
    result_llm = await service.retrieve(queries=queries, where={"user_id": "123"})
    print("  Categories:")
    for cat in result_llm.get("categories", [])[:3]:
        print(f"    - {cat.get('name')}: {(cat.get('summary') or cat.get('description', ''))[:80]}...")
    print("  Items:")
    for item in result_llm.get("items", [])[:3]:
        print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")
    if result_llm.get("resources"):
        print("  Resources:")
        for res in result_llm.get("resources", [])[:3]:
            print(f"    - [{res.get('modality')}] {res.get('url', '')[:80]}...")

    print("\n[INMEMORY] Test completed!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
