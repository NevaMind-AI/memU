# MemU OpenAgents Adapter

Long-term memory for OpenAgents networks. Give your agents persistent memory that survives restarts and spans conversations.

## Installation

```bash
pip install memu
```

## Quick Start

### Option 1: Use with Agent YAML Config

```yaml
# memory_agent.yaml
type: "openagents.agents.collaborator_agent.CollaboratorAgent"
agent_id: "memory-agent"

config:
  model_name: "gpt-4o-mini"
  provider: "openai"
  
  instruction: |
    You have long-term memory. Use memorize to store important info,
    retrieve to recall it later.

  tools:
    - name: "memorize"
      description: "Store a memory in MemU"
      implementation: "memu.adapters.openagents.tools.memorize"
      input_schema:
        type: object
        properties:
          content:
            type: string
            description: "Text to memorize"
        required: ["content"]
      
    - name: "retrieve"
      description: "Query memories"
      implementation: "memu.adapters.openagents.tools.retrieve"
      input_schema:
        type: object
        properties:
          query:
            type: string
            description: "Search query"
        required: ["query"]
```

### Option 2: Programmatic Integration

```python
from memu.app.service import MemoryService
from memu.adapters.openagents import MemUOpenAgentsAdapter

# Initialize MemU
service = MemoryService(
    llm_profiles={
        "default": {"provider": "openai", "chat_model": "gpt-4o-mini"},
        "embedding": {"provider": "openai", "embed_model": "text-embedding-3-small"},
    },
    database_config={"metadata_store": {"provider": "sqlite", "path": "memory.db"}},
)

# Create adapter
adapter = MemUOpenAgentsAdapter(service=service)
adapter.initialize(agent_id="my-agent")

# Get tools for registration
tools = adapter.get_tools()

# Or call tools directly
result = await adapter.call_tool("memorize", content="Important info")
result = await adapter.call_tool("retrieve", query="What's important?")
```

## Available Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `memorize` | Store memory | `content` |
| `retrieve` | Query memories | `query` |
| `list_memories` | List stored memories | - |
| `get_memory` | Get memory by ID | `memory_id` |

## Features

- **Semantic Search**: Find memories by meaning, not just keywords
- **Multi-modal**: Store text, conversations, documents
- **User Scoping**: Isolate memories per user/agent
- **Persistent**: SQLite, PostgreSQL, MySQL backends
- **Fast**: In-memory vector search with optional external indexes

## Example: Memory-Enhanced Agent

```python
# Agent that remembers user preferences
async def handle_message(user_id: str, message: str):
    # Check memories first
    context = await adapter.retrieve_context(
        query=message,
        user_id=user_id,
        top_k=3
    )
    
    # Process with context...
    response = await llm.chat(
        system=f"User context:\n{context}",
        user=message
    )
    
    # Store important info
    if "remember" in message.lower():
        await adapter.call_tool(
            "memorize",
            content=message,
            user_id=user_id
        )
    
    return response
```

## License

Apache 2.0
