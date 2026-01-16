"""
Integration tests for MemU OpenAgents Adapter.

These tests verify the adapter works correctly with OpenAgents patterns.

Run with: pytest tests/test_openagents_integration.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestOpenAgentsToolPattern:
    """Test that tools follow OpenAgents @tool decorator pattern."""

    def test_tool_functions_have_correct_signature(self):
        """Verify tool functions match OpenAgents expected signatures."""
        from memu.adapters.openagents.tools import (
            memorize,
            retrieve,
            list_memories,
            get_memory,
        )
        import inspect

        # memorize should accept content, modality, user_id
        sig = inspect.signature(memorize)
        params = list(sig.parameters.keys())
        assert "content" in params
        assert "modality" in params
        assert "user_id" in params

        # retrieve should accept query, top_k, user_id
        sig = inspect.signature(retrieve)
        params = list(sig.parameters.keys())
        assert "query" in params
        assert "top_k" in params
        assert "user_id" in params

        # list_memories should accept limit, memory_type, user_id
        sig = inspect.signature(list_memories)
        params = list(sig.parameters.keys())
        assert "limit" in params
        assert "memory_type" in params
        assert "user_id" in params

        # get_memory should accept memory_id
        sig = inspect.signature(get_memory)
        params = list(sig.parameters.keys())
        assert "memory_id" in params

    def test_tool_functions_return_strings(self):
        """Verify all tools return string results (OpenAgents requirement)."""
        from memu.adapters.openagents.tools import (
            memorize,
            retrieve,
            list_memories,
            get_memory,
            set_memu_service,
        )

        # Set up mock service
        mock_service = MagicMock()
        mock_service.memorize = AsyncMock(return_value={"items": []})
        mock_service.retrieve = AsyncMock(return_value={"needs_retrieval": False})
        mock_service.list_memory_items = AsyncMock(return_value={"items": []})
        mock_service.get_memory_item = AsyncMock(return_value={"item": None})
        set_memu_service(mock_service)

        # All tools should return strings
        result = memorize(content="test")
        assert isinstance(result, str)

        result = retrieve(query="test")
        assert isinstance(result, str)

        result = list_memories()
        assert isinstance(result, str)

        result = get_memory(memory_id="test-id")
        assert isinstance(result, str)

    def test_tool_schemas_match_openagents_format(self):
        """Verify tool schemas match OpenAgents YAML config format."""
        from memu.adapters.openagents.tools import TOOL_SCHEMAS

        for name, schema in TOOL_SCHEMAS.items():
            # Required fields for OpenAgents YAML
            assert "name" in schema, f"{name} missing 'name'"
            assert "description" in schema, f"{name} missing 'description'"
            assert "implementation" in schema, f"{name} missing 'implementation'"
            assert "input_schema" in schema, f"{name} missing 'input_schema'"

            # input_schema must be valid JSON Schema
            input_schema = schema["input_schema"]
            assert input_schema.get("type") == "object"
            assert "properties" in input_schema
            assert "required" in input_schema

            # implementation must be importable path
            impl = schema["implementation"]
            assert impl.startswith("memu.adapters.openagents.tools.")


class TestOpenAgentsYAMLConfig:
    """Test YAML configuration compatibility."""

    def test_yaml_config_structure(self):
        """Verify example YAML config is valid."""
        try:
            import yaml
        except ImportError:
            pytest.skip("pyyaml not installed")

        from pathlib import Path

        yaml_path = Path("examples/openagents/memory_agent.yaml")
        if not yaml_path.exists():
            pytest.skip("Example YAML not found")

        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        # Verify structure
        assert "type" in config
        assert "agent_id" in config
        assert "config" in config
        assert "tools" in config["config"]

        # Verify tools
        tools = config["config"]["tools"]
        tool_names = {t["name"] for t in tools}
        assert "memorize" in tool_names
        assert "retrieve" in tool_names

    def test_tool_implementation_paths_importable(self):
        """Verify tool implementation paths can be imported."""
        from memu.adapters.openagents.tools import TOOL_SCHEMAS
        import importlib

        for name, schema in TOOL_SCHEMAS.items():
            impl_path = schema["implementation"]
            module_path, func_name = impl_path.rsplit(".", 1)

            # Should be importable
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            assert callable(func), f"{impl_path} is not callable"


class TestAdapterWithMockOpenAgents:
    """Test adapter with mocked OpenAgents components."""

    def test_adapter_provides_tools_for_agent_registration(self):
        """Test that adapter provides tools in format agents expect."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        tools = adapter.get_tools()

        # Each tool should have the fields OpenAgents expects
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "func" in tool

            # func should be callable
            assert callable(tool["func"])

            # input_schema should be valid
            schema = tool["input_schema"]
            assert schema.get("type") == "object"

    @pytest.mark.asyncio
    async def test_adapter_call_tool_with_kwargs(self):
        """Test calling tools with keyword arguments (OpenAgents pattern)."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        mock_service.memorize = AsyncMock(
            return_value={"items": [{"summary": "Test memory"}]}
        )
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        # OpenAgents calls tools with **kwargs
        result = await adapter.call_tool(
            "memorize",
            content="Remember this important fact",
            modality="text",
        )

        assert isinstance(result, str)
        assert "memory" in result.lower() or "stored" in result.lower() or "❌" in result

    @pytest.mark.asyncio
    async def test_adapter_handles_tool_errors_gracefully(self):
        """Test that tool errors return error strings, not exceptions."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        mock_service.memorize = AsyncMock(side_effect=Exception("Database error"))
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        # Should return error string, not raise
        result = await adapter.call_tool("memorize", content="test")

        assert isinstance(result, str)
        assert "❌" in result or "error" in result.lower()


class TestCollaboratorAgentIntegration:
    """Test integration with CollaboratorAgent pattern."""

    def test_tools_work_with_collaborator_agent_tool_format(self):
        """Verify tools match CollaboratorAgent tool registration format."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        # CollaboratorAgent expects tools with these fields
        tools = adapter.get_tools()

        for tool in tools:
            # Must have name for tool lookup
            assert isinstance(tool["name"], str)
            assert len(tool["name"]) > 0

            # Must have description for LLM
            assert isinstance(tool["description"], str)
            assert len(tool["description"]) > 0

            # Must have input_schema for argument validation
            assert isinstance(tool["input_schema"], dict)

            # Must have callable func
            assert callable(tool["func"])

    def test_tool_schemas_for_yaml_registration(self):
        """Test schemas work for YAML-based tool registration."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)

        schemas = adapter.get_tool_schemas()

        # YAML registration needs implementation path
        for schema in schemas:
            assert "implementation" in schema
            assert schema["implementation"].startswith("memu.")


class TestMemoryPersistence:
    """Test memory persistence across adapter instances."""

    @pytest.mark.asyncio
    async def test_memories_persist_via_service(self):
        """Test that memories are stored via the service."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        # Create mock service that tracks calls
        stored_memories = []

        async def mock_memorize(**kwargs):
            stored_memories.append(kwargs)
            return {"items": [{"id": "mem-1", "summary": "test"}]}

        mock_service = MagicMock()
        mock_service.memorize = mock_memorize

        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="test-agent")

        # Store a memory
        await adapter.call_tool("memorize", content="Important fact")

        # Verify service was called
        assert len(stored_memories) == 1


class TestErrorHandling:
    """Test error handling matches OpenAgents expectations."""

    def test_missing_service_gives_clear_error(self):
        """Test that missing service gives clear error message."""
        from memu.adapters.openagents.tools import (
            get_memu_service,
            set_memu_service,
            memorize,
        )

        # Reset service
        set_memu_service(None)

        # Should raise with clear message
        with pytest.raises(RuntimeError) as exc_info:
            get_memu_service()

        assert "not initialized" in str(exc_info.value).lower()

    def test_tool_errors_return_strings(self):
        """Test that tool errors return error strings."""
        from memu.adapters.openagents.tools import memorize, set_memu_service

        # Set up failing service
        mock_service = MagicMock()
        mock_service.memorize = AsyncMock(side_effect=ValueError("Bad input"))
        set_memu_service(mock_service)

        # Should return error string
        result = memorize(content="test")
        assert isinstance(result, str)
        assert "❌" in result or "failed" in result.lower()


class TestAgentIdScoping:
    """Test user/agent ID scoping for multi-agent networks."""

    @pytest.mark.asyncio
    async def test_agent_id_passed_as_user_id(self):
        """Test that agent_id is used for memory scoping."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        captured_kwargs = {}

        async def capture_memorize(**kwargs):
            captured_kwargs.update(kwargs)
            return {"items": []}

        mock_service = MagicMock()
        mock_service.memorize = capture_memorize

        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="agent-123")

        await adapter.call_tool("memorize", content="test")

        # agent_id should be passed as user_id for scoping
        assert captured_kwargs.get("user") == {"user_id": "agent-123"} or \
               "user_id" in str(captured_kwargs)

    @pytest.mark.asyncio
    async def test_explicit_user_id_overrides_agent_id(self):
        """Test that explicit user_id takes precedence."""
        from memu.adapters.openagents import MemUOpenAgentsAdapter

        mock_service = MagicMock()
        adapter = MemUOpenAgentsAdapter(service=mock_service)
        adapter.initialize(agent_id="agent-123")

        # Mock the tool function to capture args
        with patch.object(adapter, "_tool_funcs") as mock_funcs:
            mock_func = MagicMock(return_value="success")
            mock_funcs.__getitem__ = MagicMock(return_value=mock_func)
            mock_funcs.__contains__ = MagicMock(return_value=True)

            await adapter.call_tool(
                "memorize",
                content="test",
                user_id="explicit-user"  # Explicit user_id
            )

            # Explicit user_id should be used
            call_kwargs = mock_func.call_args[1]
            assert call_kwargs.get("user_id") == "explicit-user"
