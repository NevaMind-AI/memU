# Quickstart: Adding Long-Term Memory to Python Agents

Welcome to MemU! This guide will help you add robust long-term memory capabilities to your Python agents in just a few minutes. Without MemU, LLMs are limited by their context window. MemU solves this by providing an intelligent, persistent memory layer.

## Prerequisites

Before we begin, ensure you have the following:

-   **Python 3.13+**: MemU takes advantage of modern Python features.
-   **OpenAI API Key**: This quickstart uses OpenAI's models (`gpt-4o-mini`). You will need a valid API key.

## Step-by-Step Guide

### 1. Installation

Install MemU using `pip` or `uv`:

```bash
pip install memu
# OR
uv add memu
```

### 2. Configuration

MemU requires an LLM backend to function. By default, it looks for the `OPENAI_API_KEY` environment variable.

**Linux / macOS / Git Bash:**
```bash
export OPENAI_API_KEY=sk-proj-your-api-key
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-proj-your-api-key"
```

### 3. The Robust Starter Script

Below is a complete, production-ready script that demonstrates the full lifecycle of a memory-enabled agent: **Initialization**, **Injection** (adding memory), and **Retrieval** (searching memory).

Create a file named `getting_started.py` and paste the following code:

```python
"""
Getting Started with MemU: A Robust Example.

This script demonstrates the core lifecycle of MemU:
1.  **Initialization**: Setting up the client with secure API key handling.
2.  **Memory Injection**: Adding a specific memory with metadata.
3.  **Retrieval**: Searching for that memory using natural language.
4.  **Error Handling**: Catching common configuration issues.

Usage:
    export OPENAI_API_KEY=your_api_key_here
    python getting_started.py
"""

import asyncio
import logging
import os
import sys

from memu.app import MemoryService

# Configure logging to show info but suppress noisy libraries
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main() -> None:
    """Run the MemU lifecycle demonstration."""
    print(">>> MemU Getting Started Example")
    print("-" * 30)

    # 1. API Key Handling
    # MemU relies on an LLM backend (defaulting to OpenAI).
    # We ensure the API key is present before proceeding.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[!] Error: OPENAI_API_KEY environment variable is not set.")
        print("Please export it: export OPENAI_API_KEY=sk-...")
        return

    try:
        # 2. Initialization
        # We initialize the MemoryService with:
        # - llm_profiles: Configuration for the LLM (model, api_key).
        # - memorize_config: Pre-defining a memory category ensures we can organize memories efficiently.
        print(f"[*] Initializing MemoryService with model: gpt-4o-mini...")
        service = MemoryService(
            llm_profiles={
                "default": {
                    "api_key": api_key,
                    "chat_model": "gpt-4o-mini",
                },
            },
            memorize_config={
                "memory_categories": [
                    {
                        "name": "User Facts",
                        "description": "General and specific facts known about the user preference and identity.",
                    }
                ]
            },
        )
        print("[OK] Service initialized successfully.\n")

        # 3. Memory Injection
        # We manually inject a memory into the system.
        # This is useful for bootstrapping a user profile or adding explicit knowledge.
        print("[*] Injecting memory...")
        memory_content = "The user is a senior Python architect who loves clean code and type hints."

        # We use 'create_memory_item' to insert a single memory record.
        # memory_type='profile' indicates this is an attribute of the user.
        result = await service.create_memory_item(
            memory_type="profile",
            memory_content=memory_content,
            memory_categories=["User Facts"],
        )
        print(f"[OK] Memory created! ID: {result.get('memory_item', {}).get('id')}\n")

        # 4. Retrieval
        # Now we query the system naturally to see if it recalls the information.
        query_text = "What kind of code does the user like?"
        print(f"[*] Querying: '{query_text}'")

        search_results = await service.retrieve(
            queries=[{"role": "user", "content": query_text}]
        )

        # 5. Display Results
        items = search_results.get("items", [])
        if items:
            print(f"[OK] Found {len(items)} relevant memory item(s):")
            for idx, item in enumerate(items, 1):
                print(f"   {idx}. {item.get('summary')} (Type: {item.get('memory_type')})")
        else:
            print("[!] No relevant memories found.")

    except Exception as e:
        print(f"\n[!] An error occurred during execution: {e}")
        logging.exception("Detailed traceback:")
    finally:
        print("\n[=] Example execution finished.")


if __name__ == "__main__":
    asyncio.run(main())
```

### Understanding the Code

1.  **Initialization**: We configure `MemoryService` with specific `llm_profiles`. This tells MemU which model to use. We also define a `memorize_config` with a "User Facts" category. Categories help the LLM organize and retrieve information more effectively.
2.  **Memory Injection**: `create_memory_item` is used to explicitly add a piece of knowledge. We tag it with `memory_type="profile"` to semantically indicate this is a user attribute.
3.  **Retrieval**: We use `retrieve` with a natural language query. MemU's internal workflow ("RAG" or "LLM" based) will determine the best way to find relevant memories.

## Troubleshooting

### `[!] Error: OPENAI_API_KEY environment variable is not set.`

This is the most common issue. It means the script cannot find your API key which is required to communicate with OpenAI.

**Solution:**
Ensure you have exported the key in your **current terminal session**.
-   **Windows PowerShell**: `$env:OPENAI_API_KEY="sk-..."`
-   **Linux/Mac**: `export OPENAI_API_KEY=sk-...`

Also, verify that you didn't accidentally include spaces around the `=` sign in bash.

## Next Steps

Now that you have the basics running, consider exploring:
-   **Core Concepts**: Learn about `MemoryService`, `MemoryItem`, and `MemoryCategory`.
-   **Advanced Configuration**: Switch to local LLMs or use different vector stores.
-   **Integrations**: Connect MemU to your existing agent framework.

## Community Resources

This tutorial was created as part of the MemU 2026 Challenge. For a summary of the architectural analysis, see the author's [LinkedIn Post](https://www.linkedin.com/posts/david-a-mamani-c_github-nevamind-aimemu-memory-infrastructure-activity-7418493617482207232-_MtG?utm_source=share&utm_medium=member_desktop&rcm=ACoAAFdc0CIB__DJovR2t1BOxxJ6tgEeOqVEgx4).
