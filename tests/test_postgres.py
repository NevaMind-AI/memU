"""
Tests for MemoryService with PostgreSQL storage backend.

These tests require a running PostgreSQL instance with pgvector extension.
To run locally:
    docker run -d \
        --name memu-postgres \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=memu \
        -p 5432:5432 \
        pgvector/pgvector:pg16
"""

import pytest


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.postgres
class TestPostgresMemorize:
    """Tests for memorize functionality with PostgreSQL storage."""

    @pytest.mark.asyncio
    async def test_memorize_conversation(
        self,
        postgres_service,
        example_conversation_path: str,
    ) -> None:
        """Test memorizing a conversation file with PostgreSQL backend."""
        memory = await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        # Verify memory structure
        assert "categories" in memory
        assert "items" in memory

        # Verify categories were created
        categories = memory.get("categories", [])
        assert len(categories) > 0

        # Verify each category has required fields
        for cat in categories:
            assert "name" in cat
            assert "id" in cat


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.postgres
class TestPostgresRetrieveRAG:
    """Tests for RAG-based retrieval with PostgreSQL storage."""

    @pytest.mark.asyncio
    async def test_retrieve_rag_returns_categories(
        self,
        postgres_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test RAG retrieval returns categories with PostgreSQL."""
        # First memorize some content
        await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        # Set method to RAG
        postgres_service.retrieve_config.method = "rag"

        # Retrieve
        result = await postgres_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_pg_123"},
        )

        # Verify result structure
        assert "categories" in result
        assert "items" in result
        assert "resources" in result
        assert "needs_retrieval" in result

        # Verify we got some results
        assert result["needs_retrieval"] is True

    @pytest.mark.asyncio
    async def test_retrieve_rag_with_items(
        self,
        postgres_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test RAG retrieval returns memory items with PostgreSQL."""
        # Memorize content
        await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        postgres_service.retrieve_config.method = "rag"
        result = await postgres_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_pg_123"},
        )

        items = result.get("items", [])
        # Verify item structure if any items returned
        for item in items:
            assert "id" in item
            assert "memory_type" in item
            assert "summary" in item


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.postgres
class TestPostgresRetrieveLLM:
    """Tests for LLM-based retrieval with PostgreSQL storage."""

    @pytest.mark.asyncio
    async def test_retrieve_llm_returns_results(
        self,
        postgres_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test LLM retrieval returns results with PostgreSQL."""
        # Memorize content first
        await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        # Set method to LLM
        postgres_service.retrieve_config.method = "llm"

        # Retrieve
        result = await postgres_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_pg_123"},
        )

        # Verify result structure
        assert "categories" in result
        assert "items" in result
        assert "resources" in result
        assert "needs_retrieval" in result

    @pytest.mark.asyncio
    async def test_retrieve_llm_category_structure(
        self,
        postgres_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test LLM retrieval returns properly structured categories with PostgreSQL."""
        await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        postgres_service.retrieve_config.method = "llm"
        result = await postgres_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_pg_123"},
        )

        categories = result.get("categories", [])
        for cat in categories:
            assert "id" in cat
            assert "name" in cat


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.postgres
class TestPostgresEndToEnd:
    """End-to-end tests for the complete workflow with PostgreSQL."""

    @pytest.mark.asyncio
    async def test_full_workflow_rag_and_llm(
        self,
        postgres_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test complete workflow with PostgreSQL: memorize -> RAG retrieve -> LLM retrieve."""
        # Step 1: Memorize
        memory = await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )
        assert len(memory.get("categories", [])) > 0

        # Step 2: RAG retrieval
        postgres_service.retrieve_config.method = "rag"
        result_rag = await postgres_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_pg_123"},
        )
        assert "categories" in result_rag

        # Step 3: LLM retrieval
        postgres_service.retrieve_config.method = "llm"
        result_llm = await postgres_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_pg_123"},
        )
        assert "categories" in result_llm

    @pytest.mark.asyncio
    async def test_memorize_creates_resource(
        self,
        postgres_service,
        example_conversation_path: str,
    ) -> None:
        """Test that memorize creates a resource entry in PostgreSQL."""
        memory = await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        # Check for resource in response (single resource case)
        if "resource" in memory:
            resource = memory["resource"]
            assert "id" in resource
            assert "modality" in resource
            assert resource["modality"] == "conversation"
        # Check for resources (multiple resources case)
        elif "resources" in memory:
            resources = memory["resources"]
            assert len(resources) > 0
            for res in resources:
                assert "id" in res
                assert "modality" in res

    @pytest.mark.asyncio
    async def test_pgvector_similarity_search(
        self,
        postgres_service,
        example_conversation_path: str,
    ) -> None:
        """Test that pgvector similarity search works correctly."""
        # Memorize to populate the database
        await postgres_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_pg_123"},
        )

        # Query for food preferences (mentioned in conversation)
        food_queries = [
            {"role": "user", "content": {"text": "What food does the user like?"}},
        ]

        postgres_service.retrieve_config.method = "rag"
        result = await postgres_service.retrieve(
            queries=food_queries,
            where={"user_id": "test_user_pg_123"},
        )

        # Should retrieve relevant items
        assert result["needs_retrieval"] is True
