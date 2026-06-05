from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POSTGRES_DSN = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/memu"
RUN_POSTGRES_TESTS_ENV = "MEMU_RUN_POSTGRES_TESTS"

# Add src to sys.path before importing memu from a source checkout.
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


async def run_postgres_workflow() -> None:
    """Run the PostgreSQL-backed memorize/retrieve smoke workflow."""
    from memu import MemoryService

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY is required for the PostgreSQL integration workflow"
        raise RuntimeError(msg)

    # Default port 5432; use 5433 if 5432 is occupied
    postgres_dsn = os.environ.get("POSTGRES_DSN", DEFAULT_POSTGRES_DSN)
    file_path = Path(__file__).resolve().parent / "example" / "example_conversation.json"

    print("\n" + "=" * 60)
    print("[POSTGRES] Starting test...")
    print(f"[POSTGRES] DSN: {postgres_dsn}")
    print("=" * 60)

    service = MemoryService(
        llm_profiles={"default": {"api_key": api_key}},
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
    memory = await service.memorize(resource_url=str(file_path), modality="conversation", user={"user_id": "123"})
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


async def test_postgres_full_workflow() -> None:
    """Opt-in pytest integration check for a local PostgreSQL + pgvector service."""
    import pytest

    if os.environ.get(RUN_POSTGRES_TESTS_ENV) != "1":
        pytest.skip(f"Set {RUN_POSTGRES_TESTS_ENV}=1 to run the PostgreSQL integration workflow")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for the PostgreSQL integration workflow")

    await run_postgres_workflow()


def main() -> int:
    asyncio.run(run_postgres_workflow())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
