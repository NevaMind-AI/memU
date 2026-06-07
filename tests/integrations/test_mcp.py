"""Unit tests for MemU MCP server integrations (FastMCP and low-level)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from memu.app.service import MemoryService
from memu.integrations.mcp_server import _MemUTools


@pytest.fixture
def mock_service() -> AsyncMock:
    """Return an AsyncMock standing in for MemoryService with canned responses."""
    service = AsyncMock(spec=MemoryService)
    service.memorize.return_value = {"status": "success"}
    service.retrieve.return_value = {
        "items": [
            {"summary": "User prefers dark mode.", "score": 0.9},
            {"summary": "User lives in Beijing.", "score": 0.7},
        ]
    }
    service.list_memory_items.return_value = {
        "items": [
            {"memory_type": "profile", "summary": "User prefers dark mode."},
            {"memory_type": "event", "summary": "User attended a meetup yesterday."},
        ]
    }
    service.list_memory_categories.return_value = {
        "categories": [
            {"name": "habits", "summary": "User drinks coffee daily."},
            {"name": "uncategorized", "description": "fallback", "summary": ""},
        ]
    }
    service.clear_memory.return_value = {"status": "success"}
    return service


class TestMemUTools:
    """Tests for the shared async tool implementations."""

    @pytest.mark.asyncio
    async def test_memorize_writes_tempfile_then_calls_service(self, mock_service: AsyncMock) -> None:
        tools = _MemUTools(mock_service)
        result = await tools.memorize("hello world", "alice")

        assert result == "Memory saved."
        assert mock_service.memorize.await_count == 1
        call = mock_service.memorize.call_args
        assert call.kwargs["modality"] == "conversation"
        assert call.kwargs["user"] == {"user_id": "alice"}
        # resource_url is a temp file path; the file is unlinked in `finally`
        assert call.kwargs["resource_url"].endswith(".txt")

    @pytest.mark.asyncio
    async def test_memorize_passes_explicit_modality(self, mock_service: AsyncMock) -> None:
        tools = _MemUTools(mock_service)
        await tools.memorize("an image caption", "alice", modality="image")
        assert mock_service.memorize.call_args.kwargs["modality"] == "image"

    @pytest.mark.asyncio
    async def test_memorize_returns_error_string_on_failure(self, mock_service: AsyncMock) -> None:
        mock_service.memorize.side_effect = RuntimeError("backend down")
        tools = _MemUTools(mock_service)
        result = await tools.memorize("x", "alice")
        assert result.startswith("Failed to save memory")

    @pytest.mark.asyncio
    async def test_retrieve_formats_top_n_summaries(self, mock_service: AsyncMock) -> None:
        tools = _MemUTools(mock_service)
        result = await tools.retrieve("dark mode?", "alice", limit=1)
        assert result == "- User prefers dark mode."
        call = mock_service.retrieve.call_args
        assert call.kwargs["queries"] == [{"role": "user", "content": "dark mode?"}]
        assert call.kwargs["where"] == {"user_id": "alice"}

    @pytest.mark.asyncio
    async def test_retrieve_no_results(self, mock_service: AsyncMock) -> None:
        mock_service.retrieve.return_value = {"items": []}
        tools = _MemUTools(mock_service)
        assert await tools.retrieve("anything", "alice") == "No relevant memories found."

    @pytest.mark.asyncio
    async def test_list_items_includes_memory_type_prefix(self, mock_service: AsyncMock) -> None:
        tools = _MemUTools(mock_service)
        result = await tools.list_items("alice")
        assert "[profile]" in result
        assert "[event]" in result
        assert "User attended a meetup yesterday." in result

    @pytest.mark.asyncio
    async def test_list_categories_falls_back_to_description(self, mock_service: AsyncMock) -> None:
        tools = _MemUTools(mock_service)
        result = await tools.list_categories("alice")
        # habits has a real summary; uncategorized falls back to its description
        assert "habits: User drinks coffee daily." in result
        assert "uncategorized: fallback" in result

    @pytest.mark.asyncio
    async def test_clear_memory_filters_by_user(self, mock_service: AsyncMock) -> None:
        tools = _MemUTools(mock_service)
        result = await tools.clear_memory("alice")
        assert "alice" in result
        assert mock_service.clear_memory.call_args.kwargs["where"] == {"user_id": "alice"}


class TestServiceFromEnv:
    """The CLI entry must work with any OpenAI-compatible provider, not just OpenAI."""

    def test_prefers_memu_api_key_over_openai_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from memu.integrations.mcp_server import _service_from_env

        monkeypatch.setenv("MEMU_API_KEY", "memu-key")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        for var in ("MEMU_BASE_URL", "MEMU_CHAT_MODEL", "MEMU_EMBED_MODEL"):
            monkeypatch.delenv(var, raising=False)

        service = _service_from_env()
        assert service.llm_profiles.profiles["default"].api_key == "memu-key"

    def test_falls_back_to_openai_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from memu.integrations.mcp_server import _service_from_env

        monkeypatch.delenv("MEMU_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        for var in ("MEMU_BASE_URL", "MEMU_CHAT_MODEL", "MEMU_EMBED_MODEL"):
            monkeypatch.delenv(var, raising=False)

        service = _service_from_env()
        assert service.llm_profiles.profiles["default"].api_key == "openai-key"

    def test_applies_optional_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from memu.integrations.mcp_server import _service_from_env

        monkeypatch.setenv("MEMU_API_KEY", "deepseek-key")
        monkeypatch.setenv("MEMU_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setenv("MEMU_CHAT_MODEL", "deepseek-chat")
        monkeypatch.setenv("MEMU_EMBED_MODEL", "deepseek-embedding")

        service = _service_from_env()
        cfg = service.llm_profiles.profiles["default"]
        assert cfg.api_key == "deepseek-key"
        assert cfg.base_url == "https://api.deepseek.com/v1"
        assert cfg.chat_model == "deepseek-chat"
        assert cfg.embed_model == "deepseek-embedding"

    def test_raises_when_no_key_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from memu.integrations.mcp_server import _service_from_env

        for var in ("MEMU_API_KEY", "OPENAI_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(RuntimeError, match="MEMU_API_KEY"):
            _service_from_env()


class TestFastMCPBuild:
    """Verify the FastMCP server exposes the five tools."""

    @pytest.mark.asyncio
    async def test_build_server_registers_five_tools(self, mock_service: AsyncMock) -> None:
        pytest.importorskip("fastmcp")
        from memu.integrations.mcp_server import build_server

        server = build_server(mock_service)
        registered = await server.list_tools()
        assert {tool.name for tool in registered} == {
            "memu_memorize",
            "memu_retrieve",
            "memu_list_items",
            "memu_list_categories",
            "memu_clear_memory",
        }


class TestLowLevelBuild:
    """Verify the low-level MCP server exposes the five tools with matching schemas."""

    @pytest.mark.asyncio
    async def test_build_server_lists_five_tools(self, mock_service: AsyncMock) -> None:
        pytest.importorskip("mcp")
        from memu.integrations.mcp_server_lowlevel import _TOOL_SCHEMA, build_server

        server = build_server(mock_service)
        assert set(_TOOL_SCHEMA.keys()) == {
            "memu_memorize",
            "memu_retrieve",
            "memu_list_items",
            "memu_list_categories",
            "memu_clear_memory",
        }
        for name, schema in _TOOL_SCHEMA.items():
            assert "user_id" in schema["inputSchema"]["required"], name
        assert "content" in _TOOL_SCHEMA["memu_memorize"]["inputSchema"]["required"]
        assert server is not None


class TestFastMCPRoundtrip:
    """End-to-end protocol roundtrip via FastMCP's in-memory client transport."""

    @pytest.mark.asyncio
    async def test_client_lists_then_calls_retrieve(self, mock_service: AsyncMock) -> None:
        pytest.importorskip("fastmcp")
        from fastmcp import Client

        from memu.integrations.mcp_server import build_server

        async with Client(build_server(mock_service)) as client:
            tools = await client.list_tools()
            assert {t.name for t in tools} == {
                "memu_memorize",
                "memu_retrieve",
                "memu_list_items",
                "memu_list_categories",
                "memu_clear_memory",
            }

            result = await client.call_tool("memu_retrieve", {"query": "dark mode?", "user_id": "alice"})
            text = "".join(block.text for block in result.content if hasattr(block, "text"))
            assert "User prefers dark mode." in text
            assert mock_service.retrieve.await_count == 1


class TestLowLevelRoundtrip:
    """End-to-end protocol roundtrip via the official mcp SDK's in-memory streams."""

    @pytest.mark.asyncio
    async def test_client_lists_then_calls_retrieve(self, mock_service: AsyncMock) -> None:
        pytest.importorskip("mcp")
        import anyio
        from mcp.client.session import ClientSession
        from mcp.shared.memory import create_client_server_memory_streams

        from memu.integrations.mcp_server_lowlevel import build_server

        server = build_server(mock_service)
        async with (
            create_client_server_memory_streams() as (client_streams, server_streams),
            anyio.create_task_group() as tg,
        ):

            async def _serve() -> None:
                await server.run(*server_streams, server.create_initialization_options())

            tg.start_soon(_serve)

            async with ClientSession(*client_streams) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert {t.name for t in tools} == {
                    "memu_memorize",
                    "memu_retrieve",
                    "memu_list_items",
                    "memu_list_categories",
                    "memu_clear_memory",
                }

                result = await session.call_tool("memu_retrieve", {"query": "dark mode?", "user_id": "alice"})
                text = "".join(b.text for b in result.content if hasattr(b, "text"))
                assert "User prefers dark mode." in text

            tg.cancel_scope.cancel()
