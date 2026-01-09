"""
Tests for MemoryService with in-memory storage backend.
"""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestInMemoryMemorize:
    """Tests for memorize functionality with in-memory storage."""

    @pytest.mark.asyncio
    async def test_memorize_conversation(
        self,
        inmemory_service,
        example_conversation_path: str,
    ) -> None:
        """Test memorizing a conversation file."""
        memory = await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
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
class TestInMemoryRetrieveRAG:
    """Tests for RAG-based retrieval with in-memory storage."""

    @pytest.mark.asyncio
    async def test_retrieve_rag_returns_categories(
        self,
        inmemory_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test RAG retrieval returns categories."""
        # First memorize some content
        await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
        )

        # Set method to RAG
        inmemory_service.retrieve_config.method = "rag"

        # Retrieve
        result = await inmemory_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_123"},
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
        inmemory_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test RAG retrieval returns memory items."""
        # Memorize content
        await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
        )

        inmemory_service.retrieve_config.method = "rag"
        result = await inmemory_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_123"},
        )

        items = result.get("items", [])
        # Verify item structure if any items returned
        for item in items:
            assert "id" in item
            assert "memory_type" in item
            assert "summary" in item


@pytest.mark.integration
@pytest.mark.slow
class TestInMemoryRetrieveLLM:
    """Tests for LLM-based retrieval with in-memory storage."""

    @pytest.mark.asyncio
    async def test_retrieve_llm_returns_results(
        self,
        inmemory_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test LLM retrieval returns results."""
        # Memorize content first
        await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
        )

        # Set method to LLM
        inmemory_service.retrieve_config.method = "llm"

        # Retrieve
        result = await inmemory_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_123"},
        )

        # Verify result structure
        assert "categories" in result
        assert "items" in result
        assert "resources" in result
        assert "needs_retrieval" in result

    @pytest.mark.asyncio
    async def test_retrieve_llm_category_structure(
        self,
        inmemory_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test LLM retrieval returns properly structured categories."""
        await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
        )

        inmemory_service.retrieve_config.method = "llm"
        result = await inmemory_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_123"},
        )

        categories = result.get("categories", [])
        for cat in categories:
            assert "id" in cat
            assert "name" in cat


@pytest.mark.integration
@pytest.mark.slow
class TestInMemoryEndToEnd:
    """End-to-end tests for the complete memorize and retrieve workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_rag_and_llm(
        self,
        inmemory_service,
        example_conversation_path: str,
        sample_queries: list[dict],
    ) -> None:
        """Test complete workflow: memorize -> RAG retrieve -> LLM retrieve."""
        # Step 1: Memorize
        memory = await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
        )
        assert len(memory.get("categories", [])) > 0

        # Step 2: RAG retrieval
        inmemory_service.retrieve_config.method = "rag"
        result_rag = await inmemory_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_123"},
        )
        assert "categories" in result_rag

        # Step 3: LLM retrieval
        inmemory_service.retrieve_config.method = "llm"
        result_llm = await inmemory_service.retrieve(
            queries=sample_queries,
            where={"user_id": "test_user_123"},
        )
        assert "categories" in result_llm

    @pytest.mark.asyncio
    async def test_memorize_creates_resource(
        self,
        inmemory_service,
        example_conversation_path: str,
    ) -> None:
        """Test that memorize creates a resource entry."""
        memory = await inmemory_service.memorize(
            resource_url=example_conversation_path,
            modality="conversation",
            user={"user_id": "test_user_123"},
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
