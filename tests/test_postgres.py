import os
from pathlib import Path

from memu.app import MemoryService


def _resolve_llm_profiles() -> dict[str, dict[str, str]]:
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_KEY")
    if gemini_key:
        base_url = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        chat_model = os.environ.get("GEMINI_CHAT_MODEL", "gemini-flash-latest")
        embed_model = os.environ.get("GEMINI_EMBED_MODEL", "text-embedding-004")
        return {
            "default": {
                "api_key": gemini_key,
                "base_url": base_url,
                "chat_model": chat_model,
                "embed_model": embed_model,
                "client_backend": "httpx",
                "provider": "gemini",
            }
        }

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY or GEMINI_API_KEY"
        raise ValueError(msg)
    return {"default": {"api_key": api_key}}


async def main():
    """Test with PostgreSQL storage."""
    # Default port 5432; use 5433 if 5432 is occupied
    postgres_dsn = os.environ.get("POSTGRES_DSN", "postgresql+psycopg://postgres:postgres@localhost:5432/memu")
    file_path = str(Path(__file__).resolve().parent / "example" / "example_conversation.json")

    print("\n" + "=" * 60)
    print("[POSTGRES] Starting test...")
    print(f"[POSTGRES] DSN: {postgres_dsn}")
    print("=" * 60)

    service = MemoryService(
        llm_profiles=_resolve_llm_profiles(),
        database_config={
            "metadata_store": {
                "provider": "postgres",
                "dsn": postgres_dsn,
                "ddl_mode": "create",
            },
            # vector_index will auto-configure to pgvector
        },
        retrieve_config={"method": "rag"},
    )

    # Memorize
    print("\n[POSTGRES] Memorizing...")
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
    print("\n[POSTGRES] RETRIEVED - RAG")
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
    print("\n[POSTGRES] RETRIEVED - LLM")
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

    print("\n[POSTGRES] Test completed!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
