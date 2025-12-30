from memu.app import MemoryService
import os

async def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    file_path = os.path.abspath("example/example_conversation.json")

    # Initialize service with RAG method
    service_rag = MemoryService(
        llm_profiles={"default": {"api_key": api_key}},
        retrieve_config={"method": "rag"}
    )

    # Memorize
    memory = await service_rag.memorize(resource_url=file_path, modality="conversation")
    for cat in memory.get('categories', []):
        print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")

    queries = [
        {"role": "user", "content": {"text": "Tell me about preferences"}},
        {"role": "user", "content": {"text": "What are their habits?"}}
    ]

    # RAG-based retrieval
    print("\n[RETRIEVED - RAG]")
    # Scope retrieval to a particular user; omit filters to fetch across scopes
    result_rag = await service_rag.retrieve(queries=queries, where={"user_id": "123"})
    for item in result_rag.get('items', [])[:3]:
        print(f"  - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")

    # LLM-based retrieval (reuse same service, switch method)
    print("\n[RETRIEVED - LLM]")
    service_rag.retrieve_config.method = "llm"
    result_llm = await service_rag.retrieve(queries=queries, where={"user_id": "123"})
    for item in result_llm.get('items', [])[:3]:
        print(f"  - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())