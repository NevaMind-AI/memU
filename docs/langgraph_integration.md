# LangGraph Integration

This integration provides a seamless way to use MemU's long-term memory capabilities within LangGraph and LangChain agents.

## Installation

Ensure you have MemU installed with the LangGraph optional dependencies:

```bash
uv sync --extra langgraph
# OR
pip install memu[langgraph]
```

## Usage

The integration exposes a helper class `MemULangGraphTools` that wraps MemU's `MemoryService` into LangChain-compatible tools.

### 1. Initialize MemoryService

First, initialize the core memory service.

```python
from memu.app.service import MemoryService

service = MemoryService()
```

### 2. Create Tools

Pass the service to the adapter to generate the tools.

```python
from memu.integrations.langgraph import MemULangGraphTools

adapter = MemULangGraphTools(service)
tools = adapter.tools()
# tools now contains [save_memory, search_memory]
```

### 3. Integrate with LangGraph

Add the tools to your LangGraph `ToolNode` or bind them to your LLM.

```python
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

# Bind tools to LLM
llm = ChatOpenAI(model="gpt-4")
llm_with_tools = llm.bind_tools(tools)

# Create ToolNode
tool_node = ToolNode(tools=tools)

# ... Build your StateGraph using tool_node ...
```

## Available Tools

### `save_memory`
Allows the agent to save important information, user preferences, or conversation snippets to long-term memory.

- **Arguments:**
  - `content` (str): The information to save.
  - `user_id` (str): The user associated with this memory.
  - `metadata` (dict, optional): Additional context (e.g., category, importance).

### `search_memory`
Allows the agent to retrieve relevant information from memory based on a query.

- **Arguments:**
  - `query` (str): The question or topic to search for.
  - `user_id` (str): The user associated with this memory.
  - `limit` (int, default=5): Number of results to return.

## Example

See `examples/langgraph_demo.py` for a complete running example of a chatbot that uses MemU to remember user details across sessions.
