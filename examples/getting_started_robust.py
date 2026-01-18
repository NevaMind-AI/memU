"""
Getting Started with MemU: A Robust Example.

This script demonstrates the core lifecycle of MemU:
1.  **Initialization**: Setting up the client with secure API key handling.
2.  **Memory Injection**: Adding a specific memory with metadata.
3.  **Retrieval**: Searching for that memory using natural language.
4.  **Error Handling**: Catching common configuration issues.

Usage:
    export OPENAI_API_KEY=your_api_key_here
    python examples/getting_started_robust.py
"""

import asyncio
import logging
import os
import sys

# Ensure src is in the path for local usage if custom installing
sys.path.insert(0, os.path.abspath("src"))

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
        print("[*] Initializing MemoryService with model: gpt-4o-mini...")
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

        search_results = await service.retrieve(queries=[{"role": "user", "content": query_text}])

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
