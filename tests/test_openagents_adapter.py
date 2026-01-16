"""
Tests for MemU OpenAgents Adapter.

Run with: pytest tests/test_openagents_adapter.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMemUOpenAgentsAdapter:
    """Tests for the MemUOpenAgentsAdapter class."""

    def test_adapter_import(self):
        """Test that adapter can be imported."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter, get_memu_tools

        assert MemUOpenAgentsAdapter is not None
        assert get_memu_tools is not None

    def test_adapter_initialization(self):
        """Test adapter initialization with mock service."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        assert adapter.service == mock_service
        assert adapter.mod_name == "memu"
        assert adapter._initialized is False

    def test_adapter_initialize(self):
        """Test adapter initialize method."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        result = adapter.initialize(agent_id="test-agent")

        assert result is True
        assert adapter.agent_id == "test-agent"
        assert adapter._initialized is True

    def test_adapter_shutdown(self):
        """Test adapter shutdown method."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        result = adapter.shutdown()

        assert result is True
        assert adapter._initialized is False

    def test_get_tools_returns_list(self):
        """Test that get_tools returns a list of tool configs."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        tools = adapter.get_tools()

        assert isinstance(tools, list)
        assert len(tools) == 4  # memorize, retrieve, list_memories, get_memory

    def test_get_tools_structure(self):
        """Test that each tool has required fields."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        tools = adapter.get_tools()

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "func" in tool
            assert callable(tool["func"])

    def test_get_tool_schemas(self):
        """Test that get_tool_schemas returns YAML-compatible schemas."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        schemas = adapter.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 4

        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "implementation" in schema
            assert "input_schema" in schema

    def test_tool_names(self):
        """Test that all expected tools are present."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        tools = adapter.get_tools()
        tool_names = {t["name"] for t in tools}

        expected = {"memorize", "retrieve", "list_memories", "get_memory"}
        assert tool_names == expected

    def test_repr(self):
        """Test adapter string representation."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        repr_str = repr(adapter)

        assert "MemUOpenAgentsAdapter" in repr_str
        assert "test-agent" in repr_str
        assert "initialized=True" in repr_str


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_memorize_schema(self):
        """Test memorize tool schema."""
        from memu.adapters.openagents.tools import TOOL_SCHEMAS

        schema = TOOL_SCHEMAS["memorize"]

        assert schema["name"] == "memorize"
        assert "content" in schema["input_schema"]["properties"]
        assert "modality" in schema["input_schema"]["properties"]
        assert "content" in schema["input_schema"]["required"]

    def test_retrieve_schema(self):
        """Test retrieve tool schema."""
        from memu.adapters.openagents.tools import TOOL_SCHEMAS

        schema = TOOL_SCHEMAS["retrieve"]

        assert schema["name"] == "retrieve"
        assert "query" in schema["input_schema"]["properties"]
        assert "top_k" in schema["input_schema"]["properties"]
        assert "query" in schema["input_schema"]["required"]

    def test_list_memories_schema(self):
        """Test list_memories tool schema."""
        from memu.adapters.openagents.tools import TOOL_SCHEMAS

        schema = TOOL_SCHEMAS["list_memories"]

        assert schema["name"] == "list_memories"
        assert "limit" in schema["input_schema"]["properties"]
        assert "memory_type" in schema["input_schema"]["properties"]

    def test_get_memory_schema(self):
        """Test get_memory tool schema."""
        from memu.adapters.openagents.tools import TOOL_SCHEMAS

        schema = TOOL_SCHEMAS["get_memory"]

        assert schema["name"] == "get_memory"
        assert "memory_id" in schema["input_schema"]["properties"]
        assert "memory_id" in schema["input_schema"]["required"]


class TestToolFunctions:
    """Tests for standalone tool functions."""

    def test_set_and_get_service(self):
        """Test service getter/setter."""
        from memu.adapters.openagents.tools import (
            get_memu_service,
            set_memu_service,
        )

        mock_service = MagicMock()
        set_memu_service(mock_service)

        result = get_memu_service()
        assert result == mock_service

    def test_get_service_raises_without_init(self):
        """Test that get_memu_service raises if not initialized."""
        from memu.adapters.openagents.tools import (
            get_memu_service,
            set_memu_service,
        )

        # Reset service
        set_memu_service(None)

        with pytest.raises(RuntimeError, match="MemU service not initialized"):
            get_memu_service()

    def test_get_memu_tools_sets_service(self):
        """Test that get_memu_tools sets the global service."""
        from memu.adapters.openagents.tools import (
            get_memu_service,
            get_memu_tools,
            set_memu_service,
        )

        # Reset
        set_memu_service(None)

        mock_service = MagicMock()
        tools = get_memu_tools(service=mock_service)

        assert len(tools) == 4
        assert get_memu_service() == mock_service


class TestAdapterCallTool:
    """Tests for adapter call_tool method."""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling unknown tool returns error."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        result = await adapter.call_tool("unknown_tool")

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_call_tool_adds_user_id(self):
        """Test that call_tool adds agent_id as user_id."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        # Mock the tool function
        with patch.object(adapter, "_tool_funcs") as mock_funcs:
            mock_func = MagicMock(return_value="success")
            mock_funcs.__getitem__ = MagicMock(return_value=mock_func)
            mock_funcs.__contains__ = MagicMock(return_value=True)

            await adapter.call_tool("memorize", content="test")

            # Verify user_id was added
            mock_func.assert_called_once()
            call_kwargs = mock_func.call_args[1]
            assert call_kwargs.get("user_id") == "test-agent"


class TestMemorizeConversation:
    """Tests for memorize_conversation helper."""

    @pytest.mark.asyncio
    async def test_memorize_conversation_formats_messages(self):
        """Test that conversation is formatted correctly."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        with patch.object(adapter, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "success"

            await adapter.memorize_conversation(messages)

            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][0] == "memorize"
            assert "[user]: Hello" in call_args[1]["content"]
            assert "[assistant]: Hi there!" in call_args[1]["content"]
            assert call_args[1]["modality"] == "conversation"


class TestRetrieveContext:
    """Tests for retrieve_context helper."""

    @pytest.mark.asyncio
    async def test_retrieve_context_calls_retrieve(self):
        """Test that retrieve_context calls retrieve tool."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        with patch.object(adapter, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "memories found"

            result = await adapter.retrieve_context("test query", top_k=3)

            mock_call.assert_called_once_with(
                "retrieve",
                query="test query",
                top_k=3,
                user_id="test-agent",
            )
            assert result == "memories found"
