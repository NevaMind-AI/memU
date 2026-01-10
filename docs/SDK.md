# MemU Python SDK

A simple, developer-friendly Python SDK for interacting with the [MemU Cloud API](https://api.memu.so).

## Installation

The SDK is included in the `memu-py` package:

```bash
pip install memu-py
```

Or install from source:

```bash
git clone https://github.com/NevaMind-AI/memU.git
cd memU
pip install -e .
```

## Quick Start

### Get Your API Key

1. Sign up at [memu.so](https://memu.so)
2. Navigate to your dashboard to obtain your API key

### Basic Usage

```python
import asyncio
from memu.sdk import MemUClient

async def main():
    # Initialize the client
    async with MemUClient(api_key="your_api_key") as client:
        # Memorize a conversation
        result = await client.memorize(
            conversation=[
                {"role": "user", "content": "I love Italian food, especially pasta."},
                {"role": "assistant", "content": "That's great! What's your favorite dish?"},
                {"role": "user", "content": "Carbonara is my absolute favorite!"}
            ],
            user_id="user_123",
            agent_id="my_assistant",
            wait_for_completion=True
        )

        print(f"Task ID: {result.task_id}")

        # Retrieve memories
        memories = await client.retrieve(
            query="What food does the user like?",
            user_id="user_123",
            agent_id="my_assistant"
        )

        print(f"Found {len(memories.items)} relevant memories")
        for item in memories.items:
            print(f"  - [{item.memory_type}] {item.content}")

asyncio.run(main())
```

### Synchronous Usage

For scripts that don't use async/await:

```python
from memu.sdk import MemUClient

# Initialize the client
client = MemUClient(api_key="your_api_key")

# Memorize a conversation (sync)
result = client.memorize_sync(
    conversation_text="User: I love pasta\nAssistant: Great choice!",
    user_id="user_123",
    agent_id="my_assistant"
)

# Retrieve memories (sync)
memories = client.retrieve_sync(
    query="What are the user's preferences?",
    user_id="user_123",
    agent_id="my_assistant"
)

# Clean up
client.close_sync()
```

## API Reference

### MemUClient

The main client class for interacting with the MemU API.

```python
MemUClient(
    api_key: str,
    *,
    base_url: str = "https://api.memu.so",
    timeout: float = 60.0,
    max_retries: int = 3
)
```

**Parameters:**
- `api_key`: Your MemU API key (required)
- `base_url`: API base URL (default: https://api.memu.so)
- `timeout`: Request timeout in seconds (default: 60.0)
- `max_retries`: Maximum retry attempts for failed requests (default: 3)

### Methods

#### `memorize()`

Memorize a conversation and extract structured memory.

```python
async def memorize(
    *,
    conversation: list[dict] | None = None,
    conversation_text: str | None = None,
    user_id: str,  # Required
    agent_id: str,  # Required
    user_name: str = "User",
    agent_name: str = "Assistant",
    session_date: str | None = None,
    wait_for_completion: bool = False,
    poll_interval: float = 2.0,
    timeout: float | None = None,
) -> MemorizeResult
```

**Parameters:**
- `conversation`: List of conversation messages `[{"role": "user", "content": "..."}]`
- `conversation_text`: Alternative: raw conversation text
- `user_id`: User ID for scoping (required)
- `agent_id`: Agent ID for scoping (required)
- `user_name`: Display name for user (default: "User")
- `agent_name`: Display name for agent (default: "Assistant")
- `session_date`: Session date in ISO format
- `wait_for_completion`: If True, poll until the task completes
- `poll_interval`: Seconds between status checks
- `timeout`: Maximum seconds to wait for completion

**Returns:** `MemorizeResult`

**Example:**
```python
result = await client.memorize(
    conversation=[
        {"role": "user", "content": "I love cooking Italian food"},
        {"role": "assistant", "content": "That's wonderful! What's your specialty?"},
    ],
    user_id="user_123",
    agent_id="cooking_assistant",
    wait_for_completion=True
)

print(f"Task ID: {result.task_id}")
```

#### `get_task_status()`

Get the status of an asynchronous memorization task.

```python
async def get_task_status(task_id: str) -> TaskStatus
```

**Parameters:**
- `task_id`: The task ID from `memorize()`

**Returns:** `TaskStatus`

**Example:**
```python
# Start memorization without waiting
result = await client.memorize(
    conversation_text="User: Hello\nAssistant: Hi there!",
    user_id="user_123",
    agent_id="agent_456"
)

# Check status later
status = await client.get_task_status(result.task_id)
print(f"Status: {status.status}")
print(f"Progress: {status.progress}%")
```

#### `retrieve()`

Retrieve relevant memories based on a query.

```python
async def retrieve(
    query: str | list[dict],
    *,
    user_id: str,  # Required
    agent_id: str,  # Required
) -> RetrieveResult
```

**Parameters:**
- `query`: Query string or list of conversation messages
- `user_id`: User ID for scoping (required)
- `agent_id`: Agent ID for scoping (required)

**Returns:** `RetrieveResult`

**Example:**
```python
# Simple text query
result = await client.retrieve(
    query="What are the user's food preferences?",
    user_id="user_123",
    agent_id="my_assistant"
)

# Conversation-aware query with context
result = await client.retrieve(
    query=[
        {"role": "user", "content": "What do they like?"},
        {"role": "assistant", "content": "They have several preferences."},
        {"role": "user", "content": "Tell me about food specifically"}
    ],
    user_id="user_123",
    agent_id="my_assistant"
)
```

#### `list_categories()`

List all memory categories.

```python
async def list_categories(
    *,
    user_id: str,  # Required
    agent_id: str | None = None,
) -> list[MemoryCategory]
```

**Parameters:**
- `user_id`: User ID for scoping (required)
- `agent_id`: Agent ID for scoping (optional)

**Returns:** List of `MemoryCategory`

**Example:**
```python
categories = await client.list_categories(user_id="user_123")
for cat in categories:
    print(f"{cat.name}: {cat.summary}")
```

### Synchronous Wrappers

All async methods have synchronous wrappers:

- `memorize_sync()` → wraps `memorize()`
- `retrieve_sync()` → wraps `retrieve()`
- `list_categories_sync()` → wraps `list_categories()`
- `get_task_status_sync()` → wraps `get_task_status()`
- `close_sync()` → wraps `close()`

## Data Models

### MemorizeResult

```python
class MemorizeResult:
    task_id: str | None          # Task ID for async tracking
    resource: MemoryResource     # Created resource
    items: list[MemoryItem]      # Extracted memory items
    categories: list[MemoryCategory]  # Updated categories
```

### RetrieveResult

```python
class RetrieveResult:
    categories: list[MemoryCategory]  # Relevant categories
    items: list[MemoryItem]           # Relevant memory items
    resources: list[MemoryResource]   # Related raw resources
    next_step_query: str | None       # Rewritten query (if applicable)
```

### MemoryItem

```python
class MemoryItem:
    id: str | None               # Unique identifier
    summary: str | None          # Summary/description
    content: str | None          # Content text
    memory_type: str | None      # Type: profile, event, preference, etc.
    category_id: str | None      # Category ID
    category_name: str | None    # Category name
    score: float | None          # Relevance score (in retrieve)
```

### MemoryCategory

```python
class MemoryCategory:
    id: str | None               # Unique identifier
    name: str | None             # Category name (e.g., 'personal info')
    summary: str | None          # Summary of content
    content: str | None          # Full content
    description: str | None      # Description
    item_count: int | None       # Number of items
    score: float | None          # Relevance score (in retrieve)
```

### TaskStatus

```python
class TaskStatus:
    task_id: str                 # Task identifier
    status: TaskStatusEnum       # PENDING, PROCESSING, COMPLETED, FAILED
    progress: float | None       # Progress percentage (0-100)
    message: str | None          # Status message or error
    result: dict | None          # Task result when completed
```

## Error Handling

The SDK provides specific exception types for different error cases:

```python
from memu.sdk.client import (
    MemUClientError,        # Base exception
    MemUAuthenticationError, # Invalid API key
    MemURateLimitError,      # Rate limit exceeded
    MemUNotFoundError,       # Resource not found
    MemUValidationError,     # Request validation failed
)

try:
    result = await client.memorize(
        conversation_text="Hello",
        user_id="user_123",
        agent_id="agent_456"
    )
except MemUAuthenticationError:
    print("Invalid API key")
except MemURateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except MemUValidationError as e:
    print(f"Validation error: {e.response}")
except MemUClientError as e:
    print(f"API error: {e.message}")
```

## Complete Example

See the full working example in [`examples/sdk_demo.py`](../examples/sdk_demo.py):

```python
"""
MemU SDK Demo - Complete Example

Demonstrates the full workflow of memorizing content and retrieving memories.
"""

import asyncio
import os
from memu.sdk import MemUClient

async def main():
    api_key = os.environ.get("MEMU_API_KEY")
    if not api_key:
        print("Please set MEMU_API_KEY environment variable")
        return

    async with MemUClient(api_key=api_key) as client:
        # 1. Memorize a conversation
        print("📝 Memorizing conversation...")
        result = await client.memorize(
            conversation=[
                {"role": "user", "content": "I love Italian food"},
                {"role": "assistant", "content": "Great taste!"},
            ],
            user_id="demo_user",
            agent_id="demo_agent",
        )

        print(f"✅ Task submitted: {result.task_id}")

        # 2. List categories
        print("\n📂 Categories:")
        categories = await client.list_categories(user_id="demo_user")
        for cat in categories:
            print(f"  - {cat.name}: {(cat.summary or '')[:60]}...")

        # 3. Retrieve memories
        print("\n🔍 Retrieving memories about preferences...")
        memories = await client.retrieve(
            query="What are the user's preferences?",
            user_id="demo_user",
            agent_id="demo_agent"
        )

        print(f"📚 Found {len(memories.items)} relevant items")
        for item in memories.items[:5]:
            print(f"  - [{item.memory_type}] {(item.content or '')[:80]}...")

        print("\n✨ Demo completed!")

if __name__ == "__main__":
    asyncio.run(main())
```

## Support

- 📚 [Full API Documentation](https://memu.pro/docs)
- 💬 [Discord Community](https://discord.gg/memu)
- 🐛 [Report Issues](https://github.com/NevaMind-AI/memU/issues)
