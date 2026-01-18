# MemU LangGraph Integration

The MemU LangGraph Integration provides a seamless adapter to expose MemU's powerful memory capabilities (`memorize` and `retrieve`) as standard [LangChain](https://python.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/) tools. This allows your agents to persist information and recall it across sessions using MemU as the long-term memory backend.

## Overview

This integration wraps the `MemoryService` and exposes two key tools:
- **`save_memory`**: Persists text, conversation snippets, or facts associated with a user.
- **`search_memory`**: Retrieves relevant memories based on semantic search queries.

These tools are fully typed and compatible with LangGraph's `prebuilt.ToolNode` and LangChain's agents.

## Installation

To use this integration, you need to install the optional dependencies:

```bash
uv add langgraph langchain-core
```

## Quick Start

Here is a complete example of how to initialize the MemU memory service and bind it to a LangGraph agent.

```python
import asyncio
import os
from memu.app.service import MemoryService
from memu.integrations.langgraph import MemULangGraphTools

# Ensure you have your configuration set (e.g., env vars for DB connection)
# os.environ["MEMU_DATABASE_URL"] = "..."

async def main():
    # 1. Initialize MemoryService
    memory_service = MemoryService()
    # If your service requires async init (check your specific implementation):
    # await memory_service.initialize()

    # 2. Instantiate MemULangGraphTools
    memu_tools = MemULangGraphTools(memory_service)

    # Get the list of tools (BaseTool compatible)
    tools = memu_tools.tools()

    # 3. Example Usage: Manually invoking a tool
    # In a real app, you would pass 'tools' to your LangGraph agent or StateGraph.

    # Save a memory
    save_tool = memu_tools.save_memory_tool()
    print("Saving memory...")
    result = await save_tool.ainvoke({
        "content": "The user prefers dark mode.",
        "user_id": "user_123",
        "metadata": {"category": "preferences"}
    })
    print(f"Save Result: {result}")

    # Search for a memory
    search_tool = memu_tools.search_memory_tool()
    print("\nSearching memory...")
    search_result = await search_tool.ainvoke({
        "query": "What are the user's preferences?",
        "user_id": "user_123"
    })
    print(f"Search Result:\n{search_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### `MemULangGraphTools`

The main adapter class.

```python
class MemULangGraphTools(memory_service: MemoryService)
```

#### `save_memory_tool() -> StructuredTool`
Returns a tool named `save_memory`.
- **Inputs**: `content` (str), `user_id` (str), `metadata` (dict, optional).
- **Description**: Save a piece of information, conversation snippet, or memory for a user.

#### `search_memory_tool() -> StructuredTool`
Returns a tool named `search_memory`.
- **Inputs**: `query` (str), `user_id` (str), `limit` (int, default=5), `metadata_filter` (dict, optional), `min_relevance_score` (float, default=0.0).
- **Description**: Search for relevant memories or information for a user based on a query.

## Troubleshooting

### Import Errors
If you see an `ImportError` regarding `langchain_core` or `langgraph`:
1. Ensure you have installed the extras: `uv add langgraph langchain-core` (or `pip install langgraph langchain-core`).
2. Verify your virtual environment is active.
