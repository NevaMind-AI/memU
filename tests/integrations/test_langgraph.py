import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src is in pythonpath if running from root without package install
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

import importlib.util

from memu.integrations.langgraph import MemUIntegrationError, MemULangGraphTools, MemUNode

# Check availability without triggering F401 (Unused import)
has_langchain = importlib.util.find_spec("langchain_core") is not None
has_langgraph = importlib.util.find_spec("langgraph") is not None

if not (has_langchain and has_langgraph):
    pytest.skip("LangGraph/LangChain not installed", allow_module_level=True)


@pytest.fixture
def mock_memory_service():
    service = MagicMock()
    service.memorize = AsyncMock()
    service.retrieve = AsyncMock()
    return service


@pytest.fixture
def langgraph_tools(mock_memory_service):
    return MemULangGraphTools(mock_memory_service)


def test_memu_langgraph_tools_initialization(mock_memory_service):
    """Verify MemULangGraphTools initializes correctly."""
    tools_bucket = MemULangGraphTools(mock_memory_service)
    assert tools_bucket.memory_service == mock_memory_service
    tools = tools_bucket.tools()
    assert len(tools) == 2
    assert tools[0].name == "save_memory"
    assert tools[1].name == "search_memory"


@pytest.mark.asyncio
async def test_save_memory_tool_execution(langgraph_tools, mock_memory_service):
    """Verify save_memory_tool calls memorize with correct parameters."""
    save_tool = langgraph_tools.save_memory_tool()

    # Tool arguments
    content = "This is a test memory."
    user_id = "user_123"
    metadata = {"category": "test"}

    # Execute the tool's coroutine directly
    result = await save_tool.coroutine(content=content, user_id=user_id, metadata=metadata)

    assert result == "Memory saved successfully."

    # Verify memorize was called once
    mock_memory_service.memorize.assert_called_once()

    # Check arguments
    call_args = mock_memory_service.memorize.call_args
    _, kwargs = call_args

    assert kwargs["modality"] == "conversation"
    assert kwargs["user"]["user_id"] == user_id
    assert kwargs["user"]["category"] == "test"

    # Verify a temporary file was passed as resource_url
    resource_url = kwargs["resource_url"]
    assert "memu_input_" in resource_url
    assert resource_url.endswith(".txt")

    # Verify cleanup works
    assert not os.path.exists(resource_url), "Temporary file should have been cleaned up."


@pytest.mark.asyncio
async def test_save_memory_error_handling(langgraph_tools, mock_memory_service):
    """Verify save_memory_tool handles service errors by raising custom exceptions."""
    save_tool = langgraph_tools.save_memory_tool()

    # Mock service to raise an exception
    mock_memory_service.memorize.side_effect = Exception("Service unavailable")

    with pytest.raises(MemUIntegrationError) as exc_info:
        await save_tool.coroutine(content="Fail", user_id="user_123")

    assert "Failed to save memory" in str(exc_info.value)
    assert "Service unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_memory_tool_execution(langgraph_tools, mock_memory_service):
    """Verify search_memory_tool calls retrieve and formats output."""
    search_tool = langgraph_tools.search_memory_tool()

    query = "What is my name?"
    user_id = "user_123"

    # Mock return value from retrieve
    mock_memory_service.retrieve.return_value = {
        "items": [{"summary": "User name is David", "score": 0.9}, {"summary": "User likes Python", "score": 0.8}]
    }

    result = await search_tool.coroutine(query=query, user_id=user_id)

    # Check expected format
    assert "Retrieved Memories:" in result
    assert "[Score: 0.9] User name is David" in result
    assert "[Score: 0.8] User likes Python" in result

    # Verify key args
    mock_memory_service.retrieve.assert_called_once()
    _, kwargs = mock_memory_service.retrieve.call_args

    assert kwargs["queries"][0]["content"] == query
    assert kwargs["where"]["user_id"] == user_id


@pytest.mark.asyncio
async def test_search_memory_with_metadata_filter(langgraph_tools, mock_memory_service):
    """Verify search_memory_tool passes metadata filters correctly."""
    search_tool = langgraph_tools.search_memory_tool()

    query = "Search with filter"
    user_id = "user_123"
    metadata_filter = {"category": "work"}

    mock_memory_service.retrieve.return_value = {"items": []}

    await search_tool.coroutine(query=query, user_id=user_id, metadata_filter=metadata_filter)

    # Verify where filter includes metadata
    _, kwargs = mock_memory_service.retrieve.call_args
    assert kwargs["where"]["user_id"] == user_id
    assert kwargs["where"]["category"] == "work"


@pytest.mark.asyncio
async def test_search_memory_error_handling(langgraph_tools, mock_memory_service):
    """Verify search_memory_tool handles service errors by raising custom exceptions."""
    search_tool = langgraph_tools.search_memory_tool()

    mock_memory_service.retrieve.side_effect = Exception("Network timeout")

    with pytest.raises(MemUIntegrationError) as exc_info:
        await search_tool.coroutine(query="Test", user_id="user_123")

    assert "Failed to search memory" in str(exc_info.value)
    assert "Network timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_memu_node_execution(mock_memory_service):
    """Verify MemUNode initializes and executes correctly."""
    node = MemUNode(mock_memory_service)

    # Test tool retrieval
    tools = node.get_tools()
    assert len(tools) == 2

    # Test node call
    state: dict[str, list[Any]] = {"messages": []}
    result = await node(state)

    assert result == {"memu_status": "active"}
