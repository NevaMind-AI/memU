"""Tests for the MCP integration module."""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import AsyncMock

import pytest

from memu.app.service import MemoryService
from memu.integrations.mcp import (
    MCPUserModel,
    _build_scope,
    _get_service,
    clear_memory,
    create_memory,
    delete_memory,
    init_mcp_server,
    list_categories,
    list_memories,
    memorize,
    retrieve,
    update_memory,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_llm_client() -> AsyncMock:
    """Create a mock LLM client that handles chat and embed calls."""
    client = AsyncMock()
    client.chat = AsyncMock(
        return_value=(
            "<profile>\n"
            "  <memory>\n"
            "    <content>User likes coffee</content>\n"
            "    <categories><category>preferences</category></categories>\n"
            "  </memory>\n"
            "</profile>"
        )
    )
    client.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    client.chat_model = "mock-model"
    client.embed_model = "mock-embed"
    return client


def _make_service() -> MemoryService:
    """Create a MemoryService with inmemory backend and MCPUserModel scope."""
    service = MemoryService(
        llm_profiles={
            "default": {
                "api_key": "test-key",
                "chat_model": "test-model",
            },
        },
        database_config={"metadata_store": {"provider": "inmemory"}},
        user_config={"model": MCPUserModel},
        memorize_config={"memory_categories": []},
    )
    mock_client = _make_mock_llm_client()
    service._llm_clients["default"] = mock_client
    service._llm_clients["embedding"] = mock_client
    return service


def _insert_item(service: MemoryService, summary: str, user_data: dict[str, Any]) -> str:
    """Directly insert a memory item into the store, bypassing the workflow pipeline."""
    store = service.database
    item = store.memory_item_repo.create_item(
        resource_id="",
        memory_type="profile",
        summary=summary,
        embedding=[0.1, 0.2, 0.3],
        user_data=user_data,
    )
    return item.id


@pytest.fixture()
def service():
    svc = _make_service()
    init_mcp_server(svc)
    yield svc
    import memu.integrations.mcp as mcp_mod

    mcp_mod._service = None


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestBuildScope:
    def test_user_id_only(self):
        assert _build_scope("alice") == {"user_id": "alice"}

    def test_full_scope(self):
        result = _build_scope("alice", agent_id="agent-1", session_id="sess-1")
        assert result == {"user_id": "alice", "agent_id": "agent-1", "session_id": "sess-1"}

    def test_none_fields_excluded(self):
        result = _build_scope("alice", agent_id=None, session_id="sess-1")
        assert "agent_id" not in result
        assert result["session_id"] == "sess-1"


class TestGetService:
    def test_raises_when_not_initialized(self):
        import memu.integrations.mcp as mcp_mod

        mcp_mod._service = None
        with pytest.raises(RuntimeError, match="MemoryService not initialized"):
            _get_service()


class TestMCPUserModel:
    def test_fields(self):
        model = MCPUserModel(user_id="u1", agent_id="a1", session_id="s1")
        assert model.user_id == "u1"
        assert model.agent_id == "a1"
        assert model.session_id == "s1"

    def test_defaults_to_none(self):
        model = MCPUserModel()
        assert model.user_id is None
        assert model.agent_id is None
        assert model.session_id is None

    def test_normalize_where_accepts_all_fields(self, service):
        """MCPUserModel fields should be recognized by _normalize_where."""
        where = {"user_id": "u1", "agent_id": "a1", "session_id": "s1"}
        result = service._normalize_where(where)
        assert result == where

    def test_normalize_where_rejects_unknown_field(self, service):
        with pytest.raises(ValueError, match="Unknown filter field"):
            service._normalize_where({"unknown_field": "value"})


# ---------------------------------------------------------------------------
# Tool tests: list and scope isolation (using direct store inserts)
# ---------------------------------------------------------------------------


class TestListMemories:
    async def test_list_returns_items(self, service):
        _insert_item(service, "Memory A", {"user_id": "user-1"})
        _insert_item(service, "Memory B", {"user_id": "user-1"})

        result = json.loads(await list_memories(user_id="user-1"))
        assert len(result["items"]) == 2
        summaries = {item["summary"] for item in result["items"]}
        assert summaries == {"Memory A", "Memory B"}

    async def test_list_empty(self, service):
        result = json.loads(await list_memories(user_id="user-1"))
        assert result["items"] == []


class TestListCategories:
    async def test_list_categories_empty(self, service):
        result = json.loads(await list_categories(user_id="user-1"))
        assert "categories" in result
        assert isinstance(result["categories"], list)


class TestUserScopeIsolation:
    async def test_different_users_isolated(self, service):
        _insert_item(service, "Alice memory", {"user_id": "alice"})
        _insert_item(service, "Bob memory", {"user_id": "bob"})

        alice_items = json.loads(await list_memories(user_id="alice"))
        bob_items = json.loads(await list_memories(user_id="bob"))

        assert len(alice_items["items"]) == 1
        assert alice_items["items"][0]["summary"] == "Alice memory"
        assert len(bob_items["items"]) == 1
        assert bob_items["items"][0]["summary"] == "Bob memory"

    async def test_agent_id_isolation(self, service):
        _insert_item(service, "Agent A memory", {"user_id": "user-1", "agent_id": "agent-A"})
        _insert_item(service, "Agent B memory", {"user_id": "user-1", "agent_id": "agent-B"})

        items_a = json.loads(await list_memories(user_id="user-1", agent_id="agent-A"))
        items_b = json.loads(await list_memories(user_id="user-1", agent_id="agent-B"))

        assert len(items_a["items"]) == 1
        assert items_a["items"][0]["summary"] == "Agent A memory"
        assert len(items_b["items"]) == 1
        assert items_b["items"][0]["summary"] == "Agent B memory"

    async def test_session_id_isolation(self, service):
        _insert_item(service, "Session 1 memory", {"user_id": "user-1", "session_id": "sess-1"})
        _insert_item(service, "Session 2 memory", {"user_id": "user-1", "session_id": "sess-2"})

        items_1 = json.loads(await list_memories(user_id="user-1", session_id="sess-1"))
        items_2 = json.loads(await list_memories(user_id="user-1", session_id="sess-2"))

        assert len(items_1["items"]) == 1
        assert items_1["items"][0]["summary"] == "Session 1 memory"
        assert len(items_2["items"]) == 1
        assert items_2["items"][0]["summary"] == "Session 2 memory"

    async def test_full_scope_isolation(self, service):
        _insert_item(service, "Scoped memory", {"user_id": "u1", "agent_id": "a1", "session_id": "s1"})

        all_user = json.loads(await list_memories(user_id="u1"))
        assert len(all_user["items"]) == 1

        scoped = json.loads(await list_memories(user_id="u1", agent_id="a1", session_id="s1"))
        assert len(scoped["items"]) == 1

        wrong_agent = json.loads(await list_memories(user_id="u1", agent_id="a2"))
        assert len(wrong_agent["items"]) == 0

        wrong_session = json.loads(await list_memories(user_id="u1", agent_id="a1", session_id="s2"))
        assert len(wrong_session["items"]) == 0


class TestDeleteMemory:
    async def test_delete_removes_item(self, service):
        item_id = _insert_item(service, "To be deleted", {"user_id": "user-1"})

        items_before = json.loads(await list_memories(user_id="user-1"))
        assert len(items_before["items"]) == 1

        result = json.loads(await delete_memory(memory_id=item_id, user_id="user-1"))
        assert result["memory_item"]["id"] == item_id

        items_after = json.loads(await list_memories(user_id="user-1"))
        assert len(items_after["items"]) == 0


class TestClearMemory:
    async def test_clear_removes_all(self, service):
        _insert_item(service, "Memory 1", {"user_id": "user-1"})
        _insert_item(service, "Memory 2", {"user_id": "user-1"})

        items_before = json.loads(await list_memories(user_id="user-1"))
        assert len(items_before["items"]) == 2

        await clear_memory(user_id="user-1")

        items_after = json.loads(await list_memories(user_id="user-1"))
        assert len(items_after["items"]) == 0

    async def test_clear_scope_isolation(self, service):
        _insert_item(service, "User A memory", {"user_id": "user-A"})
        _insert_item(service, "User B memory", {"user_id": "user-B"})

        await clear_memory(user_id="user-A")

        items_a = json.loads(await list_memories(user_id="user-A"))
        items_b = json.loads(await list_memories(user_id="user-B"))
        assert len(items_a["items"]) == 0
        assert len(items_b["items"]) == 1


# ---------------------------------------------------------------------------
# Tool tests: memorize and retrieve (through pipeline with mocked LLM)
# ---------------------------------------------------------------------------


class TestMemorize:
    async def test_memorize_calls_service(self, service):
        expected = {"categories": [{"name": "preferences"}], "resources": []}
        service.memorize = AsyncMock(return_value=expected)

        result_json = await memorize(content="Hello world", user_id="user-1")
        result = json.loads(result_json)
        assert result == expected

        call_kwargs = service.memorize.call_args.kwargs
        assert call_kwargs["modality"] == "conversation"
        assert call_kwargs["user"] == {"user_id": "user-1"}
        assert call_kwargs["resource_url"].endswith(".txt")

    async def test_memorize_with_scope(self, service):
        service.memorize = AsyncMock(return_value={"categories": []})

        await memorize(
            content="Scoped content",
            user_id="user-1",
            agent_id="agent-1",
            session_id="sess-1",
        )

        call_kwargs = service.memorize.call_args.kwargs
        assert call_kwargs["user"] == {
            "user_id": "user-1",
            "agent_id": "agent-1",
            "session_id": "sess-1",
        }

    async def test_memorize_custom_modality(self, service):
        service.memorize = AsyncMock(return_value={})

        await memorize(content="Test", user_id="user-1", modality="document")

        call_kwargs = service.memorize.call_args.kwargs
        assert call_kwargs["modality"] == "document"

    async def test_memorize_cleans_up_temp_file(self, service):
        captured_path = {}

        async def capture_memorize(**kwargs):
            captured_path["url"] = kwargs["resource_url"]
            assert os.path.exists(kwargs["resource_url"])
            with open(kwargs["resource_url"]) as f:
                assert f.read() == "temp file test"
            return {}

        service.memorize = capture_memorize

        await memorize(content="temp file test", user_id="user-1")

        assert not os.path.exists(captured_path["url"])


class TestRetrieve:
    async def test_retrieve_calls_service(self, service):
        expected = {"items": [{"summary": "User likes coffee"}], "categories": []}
        service.retrieve = AsyncMock(return_value=expected)

        result_json = await retrieve(query="What are user preferences?", user_id="user-1")
        result = json.loads(result_json)
        assert result == expected

        service.retrieve.assert_awaited_once_with(
            queries=[{"role": "user", "content": {"text": "What are user preferences?"}}],
            where={"user_id": "user-1"},
        )

    async def test_retrieve_with_scope(self, service):
        service.retrieve = AsyncMock(return_value={"items": [], "categories": []})

        await retrieve(
            query="Test query",
            user_id="user-1",
            agent_id="agent-1",
            session_id="sess-1",
        )

        service.retrieve.assert_awaited_once_with(
            queries=[{"role": "user", "content": {"text": "Test query"}}],
            where={"user_id": "user-1", "agent_id": "agent-1", "session_id": "sess-1"},
        )


# ---------------------------------------------------------------------------
# Tool tests: create_memory / update_memory (mock service methods)
# ---------------------------------------------------------------------------


class TestCreateMemoryTool:
    async def test_create_memory_calls_service(self, service):
        expected = {"memory_item": {"id": "test-id", "summary": "Test"}, "category_updates": []}
        service.create_memory_item = AsyncMock(return_value=expected)

        result_json = await create_memory(
            content="Test memory",
            user_id="user-1",
            memory_type="profile",
            categories=["cat-1"],
        )
        result = json.loads(result_json)
        assert result == expected

        service.create_memory_item.assert_awaited_once_with(
            memory_type="profile",
            memory_content="Test memory",
            memory_categories=["cat-1"],
            user={"user_id": "user-1"},
        )

    async def test_create_memory_with_scope(self, service):
        expected = {"memory_item": {"id": "test-id", "summary": "Test"}, "category_updates": []}
        service.create_memory_item = AsyncMock(return_value=expected)

        await create_memory(
            content="Scoped memory",
            user_id="user-1",
            agent_id="agent-1",
            session_id="sess-1",
            memory_type="knowledge",
            categories=[],
        )

        service.create_memory_item.assert_awaited_once_with(
            memory_type="knowledge",
            memory_content="Scoped memory",
            memory_categories=[],
            user={"user_id": "user-1", "agent_id": "agent-1", "session_id": "sess-1"},
        )

    async def test_create_memory_default_categories(self, service):
        service.create_memory_item = AsyncMock(return_value={"memory_item": {}, "category_updates": []})

        await create_memory(content="Test", user_id="user-1")

        call_kwargs = service.create_memory_item.call_args.kwargs
        assert call_kwargs["memory_categories"] == []


class TestUpdateMemoryTool:
    async def test_update_memory_calls_service(self, service):
        expected = {"memory_item": {"id": "m1", "summary": "Updated"}, "category_updates": []}
        service.update_memory_item = AsyncMock(return_value=expected)

        result_json = await update_memory(
            memory_id="m1",
            user_id="user-1",
            content="Updated content",
            memory_type="event",
            categories=["cat-1"],
        )
        result = json.loads(result_json)
        assert result == expected

        service.update_memory_item.assert_awaited_once_with(
            memory_id="m1",
            memory_type="event",
            memory_content="Updated content",
            memory_categories=["cat-1"],
            user={"user_id": "user-1"},
        )

    async def test_update_memory_partial(self, service):
        service.update_memory_item = AsyncMock(return_value={"memory_item": {}, "category_updates": []})

        await update_memory(
            memory_id="m1",
            user_id="user-1",
            content="New content only",
        )

        call_kwargs = service.update_memory_item.call_args.kwargs
        assert call_kwargs["memory_content"] == "New content only"
        assert call_kwargs["memory_type"] is None
        assert call_kwargs["memory_categories"] is None
