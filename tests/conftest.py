"""
Shared pytest fixtures and configuration for memU tests.
"""

import os
from pathlib import Path

import pytest

from memu.app import MemoryService


@pytest.fixture(scope="session")
def openai_api_key() -> str | None:
    """Get OpenAI API key from environment."""
    return os.environ.get("OPENAI_API_KEY")


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    """Get PostgreSQL DSN from environment or use default."""
    return os.environ.get("POSTGRES_DSN", "postgresql+psycopg://postgres:postgres@localhost:5432/memu")


@pytest.fixture(scope="session")
def example_conversation_path() -> str:
    """Get the path to the example conversation file."""
    tests_dir = Path(__file__).parent
    return str(tests_dir / "example" / "example_conversation.json")


@pytest.fixture
def inmemory_service(openai_api_key: str | None) -> MemoryService:
    """Create a MemoryService with in-memory storage."""
    if not openai_api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    return MemoryService(
        llm_profiles={"default": {"api_key": openai_api_key}},
        database_config={
            "metadata_store": {"provider": "inmemory"},
        },
        retrieve_config={"method": "rag"},
    )


@pytest.fixture
def postgres_service(openai_api_key: str | None, postgres_dsn: str) -> MemoryService:
    """Create a MemoryService with PostgreSQL storage."""
    if not openai_api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    try:
        service = MemoryService(
            llm_profiles={"default": {"api_key": openai_api_key}},
            database_config={
                "metadata_store": {
                    "provider": "postgres",
                    "dsn": postgres_dsn,
                    "ddl_mode": "create",
                },
            },
            retrieve_config={"method": "rag"},
        )
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")
    else:
        return service


@pytest.fixture
def sample_queries() -> list[dict]:
    """Sample queries for testing retrieval."""
    return [
        {"role": "user", "content": {"text": "Tell me about preferences"}},
        {"role": "assistant", "content": {"text": "Sure, I'll tell you about their preferences"}},
        {"role": "user", "content": {"text": "What are they"}},
    ]
