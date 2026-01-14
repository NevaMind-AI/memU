"""Test SQLite database backend for MemU."""

import os
import tempfile

from memu.app import MemoryService


def _print_results(title: str, result: dict) -> None:
    print(f"\n[SQLITE] RETRIEVED - {title}")
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


async def main():
    """Test with SQLite storage."""
    api_key = os.environ.get("OPENAI_API_KEY")
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "example", "example_conversation.json"))

    # Create a temporary SQLite database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        sqlite_path = tmp.name

    sqlite_dsn = f"sqlite:///{sqlite_path}"

    print("\n" + "=" * 60)
    print("[SQLITE] Starting test...")
    print(f"[SQLITE] DSN: {sqlite_dsn}")
    print("=" * 60)

    try:
        service = MemoryService(
            llm_profiles={"default": {"api_key": api_key}},
            database_config={
                "metadata_store": {
                    "provider": "sqlite",
                    "dsn": sqlite_dsn,
                },
                # SQLite uses brute-force vector search
                "vector_index": {"provider": "bruteforce"},
            },
            retrieve_config={"method": "rag"},
        )

        # Memorize
        print("\n[SQLITE] Memorizing...")
        memory = await service.memorize(resource_url=file_path, modality="conversation", user={"user_id": "123"})
        for cat in memory.get("categories", []):
            print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")

        queries = [
            {"role": "user", "content": {"text": "Tell me about preferences"}},
            {"role": "assistant", "content": {"text": "Sure, I'll tell you about their preferences"}},
            {
                "role": "user",
                "content": {"text": "What are they"},
            },  # This is the query that will be used to retrieve the memory
        ]

        # RAG-based retrieval
        service.retrieve_config.method = "rag"
        result_rag = await service.retrieve(queries=queries, where={"user_id": "123"})
        _print_results("RAG", result_rag)

        # LLM-based retrieval
        service.retrieve_config.method = "llm"
        result_llm = await service.retrieve(queries=queries, where={"user_id": "123"})
        _print_results("LLM", result_llm)

        print("\n[SQLITE] Test completed!")

    finally:
        # Clean up the temporary database file
        if os.path.exists(sqlite_path):
            os.unlink(sqlite_path)
            print(f"[SQLITE] Cleaned up temporary database: {sqlite_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
