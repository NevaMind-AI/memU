from typing import Any

import aiohttp
from claude_agent_sdk import create_sdk_mcp_server, tool

BASE_URL = "https://api.memu.so"
API_KEY = "your memu api key"
USER_ID = "claude_user"
AGENT_ID = "claude_agent"


@tool("memu_memory", "Retrieve memory based on a query", {"query": str})
async def get_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve memory from the memory API based on the provided query."""
    query = args["query"]
    url = f"{BASE_URL}/api/v3/memory/retrieve"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {"user_id": USER_ID, "agent_id": AGENT_ID, "query": query}

    async with aiohttp.ClientSession() as session, session.post(url, headers=headers, json=data) as response:
        result = await response.json()

    return {"content": [{"type": "text", "text": str(result)}]}


async def _get_todos() -> str:
    url = f"{BASE_URL}/api/v3/memory/categories"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {
        "user_id": USER_ID,
        "agent_id": AGENT_ID,
    }
    async with aiohttp.ClientSession() as session, session.post(url, headers=headers, json=data) as response:
        result = await response.json()

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
