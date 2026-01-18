"""Unit tests for MemU LangGraph integration."""

from unittest.mock import AsyncMock

import pytest

# Import guard using pytest.importorskip
langgraph = pytest.importorskip("langgraph")
from langchain_core.tools import StructuredTool  # noqa: E402

from memu.app.service import MemoryService  # noqa: E402
from memu.integrations.langgraph import MemULangGraphTools  # noqa: E402


@pytest.fixture
def mock_memory_service():
    """Fixture for a mocked MemoryService."""
    service = AsyncMock(spec=MemoryService)
    # Mock return values for methods if necessary
    service.memorize.return_value = {"status": "success"}
    service.retrieve.return_value = {
        "items": [
            {"summary": "Test memory 1", "score": 0.9},
            {"summary": "Test memory 2", "score": 0.5},
        ]
    }
    return service


@pytest.mark.asyncio
async def test_adapter_initialization(mock_memory_service):
    """Test that the adapter initializes and exposes tools."""
    adapter = MemULangGraphTools(mock_memory_service)
    tools = adapter.tools()

    assert len(tools) == 2
    assert any(t.name == "save_memory" for t in tools)
    assert any(t.name == "search_memory" for t in tools)

    # Strictly verify that we are returning LangChain/LangGraph compatible tools
    assert isinstance(tools[0], StructuredTool)


@pytest.mark.asyncio
async def test_save_memory_tool_execution(mock_memory_service):
    """Test the save_memory tool execution logic."""
    adapter = MemULangGraphTools(mock_memory_service)
    save_tool = adapter.save_memory_tool()

    inputs = {"content": "Test content", "user_id": "user_123", "metadata": {"key": "val"}}

    result = await save_tool.ainvoke(inputs)

    assert "saved successfully" in result
    # Verify service was called with correct structure
    mock_memory_service.memorize.assert_called_once()
    call_args = mock_memory_service.memorize.call_args
    assert "user_id" in call_args.kwargs["user"]
    assert call_args.kwargs["user"]["user_id"] == "user_123"


@pytest.mark.asyncio
async def test_search_memory_tool_execution(mock_memory_service):
    """Test the search_memory tool execution logic."""
    adapter = MemULangGraphTools(mock_memory_service)
    search_tool = adapter.search_memory_tool()

    inputs = {"query": "Test query", "user_id": "user_123"}

    result = await search_tool.ainvoke(inputs)

    assert "Test memory 1" in result
    mock_memory_service.retrieve.assert_called_once()


def test_import_langgraph_dep():
    """Verify strictly that langgraph is importable and used."""
    import langgraph

    assert langgraph is not None
