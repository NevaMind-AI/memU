from typing import Any

import httpx

from ..claude_sdk import create_sdk_mcp_server, tool
from .common import get_platform_memory_config


@tool("memu_memory", "Retrieve memory based on a query", {"query": str})
async def get_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve memory from the memory API based on the provided query."""
    query = args["query"]
    config = get_platform_memory_config()
    url = f"{config.base_url}/api/v3/memory/retrieve"
    headers = {"Authorization": f"Bearer {config.api_key}"}
    data = {"user_id": config.user_id, "agent_id": config.agent_id, "query": query}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

    return {"content": [{"type": "text", "text": str(result)}]}


async def _get_todos() -> str:
    config = get_platform_memory_config()
    url = f"{config.base_url}/api/v3/memory/categories"
    headers = {"Authorization": f"Bearer {config.api_key}"}
    data = {
        "user_id": config.user_id,
        "agent_id": config.agent_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

    categories = result["categories"]
    todos = ""
    for category in categories:
        if category["name"] == "todo":
            todos = category["summary"]
    return todos


@tool("memu_todos", "Retrieve todos for the user", {})
async def get_todos() -> dict[str, Any]:
    """Retrieve todos from the memory API."""
    todos = await _get_todos()
    return {"content": [{"type": "text", "text": str(todos)}]}


# Create the MCP server with the tool
memu_server = create_sdk_mcp_server(name="memu", version="1.0.0", tools=[get_memory, get_todos])
