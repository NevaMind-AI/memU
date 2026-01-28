from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .common import get_memory_service

USER_ID = "claude_user"


@tool("memu_memory", "Retrieve memory based on a query", {"query": str})
async def get_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve memory from the memory API based on the provided query."""
    query = {"role": "user", "content": args["query"]}

    memory_service = get_memory_service()

    result = await memory_service.retrieve(query, where={"user_id": USER_ID})

    return {"content": [{"type": "text", "text": str(result)}]}


async def _get_todos() -> str:
    memory_service = get_memory_service()

    result = await memory_service.list_memory_categories(where={"user_id": USER_ID})

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


memu_server = create_sdk_mcp_server(name="memu", version="1.0.0", tools=[get_memory, get_todos])
