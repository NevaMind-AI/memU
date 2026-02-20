import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from memu.integrations.mcp import MemUMCPServer


@pytest.fixture
def mock_memory_service():
    service = MagicMock()
    # Mock return values for different methods
    service.retrieve = AsyncMock(return_value={"items": [{"content": "Test Result"}]})
    service.memorize = AsyncMock(return_value={"status": "memorized"})
    service.list_memory_items = AsyncMock(return_value={"items": []})
    service.list_memory_categories = AsyncMock(return_value={"categories": []})
    service.create_memory_item = AsyncMock(return_value={"id": "new_item"})
    service.update_memory_item = AsyncMock(return_value={"id": "updated_item"})
    service.delete_memory_item = AsyncMock(return_value={"id": "deleted_item"})
    return service


@pytest.fixture
def mcp_server(mock_memory_service):
    return MemUMCPServer(mock_memory_service, name="test-mcp")


@pytest.mark.asyncio
async def test_get_memory(mcp_server, mock_memory_service):
    get_memory = mcp_server.mcp._tool_manager._tools["get_memory"].fn
    result_str = await get_memory(query="hello")
    result = json.loads(result_str)

    assert "Test Result" in result["items"][0]["content"]
    mock_memory_service.retrieve.assert_called_once()


@pytest.mark.asyncio
async def test_memorize(mcp_server, mock_memory_service):
    memorize = mcp_server.mcp._tool_manager._tools["memorize"].fn
    result_str = await memorize(content="new fact", user_id="user1")
    result = json.loads(result_str)

    assert result["status"] == "memorized"
    mock_memory_service.memorize.assert_called_once_with(
        resource_url="new fact", modality="conversation", user={"user_id": "user1"}
    )


@pytest.mark.asyncio
async def test_search_items(mcp_server, mock_memory_service):
    search_items = mcp_server.mcp._tool_manager._tools["search_items"].fn
    await search_items(query="find me", limit=10)

    mock_memory_service.list_memory_items.assert_called_once_with(
        query="find me", where={"user_id": "default_user"}, limit=10
    )


@pytest.mark.asyncio
async def test_create_memory_item(mcp_server, mock_memory_service):
    create_tool = mcp_server.mcp._tool_manager._tools["create_memory_item"].fn
    await create_tool(content="some fact", categories=["facts"], memory_type="fact")

    mock_memory_service.create_memory_item.assert_called_once_with(
        memory_type="fact",
        memory_content="some fact",
        memory_categories=["facts"],
        user={"user_id": "default_user"},
    )
