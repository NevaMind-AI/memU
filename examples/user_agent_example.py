"""
Example demonstrating the new user_id and agent_id support with SQLite and vector database persistence.

This example shows:
1. How to initialize MemoryService with user_id and agent_id
2. How to use SQLite for persistent storage
3. How to use the vector database for embeddings
4. How to work with multiple users and agents
"""

import asyncio

from memu.app.service import MemoryService
from memu.app.settings import BlobConfig, DatabaseConfig, LLMConfig
from memu.storage.migrations import backup_database, migrate_database


async def example_single_user_agent():
    """Example: Single user and agent with persistent storage."""
    print("=== Example 1: Single user and agent with persistent storage ===\n")

    # Initialize service with user_id and agent_id
    service = MemoryService(
        user_id="user123",
        agent_id="assistant_v1",
        llm_config=LLMConfig(
            base_url="https://api.openai.com/v1",
            api_key="YOUR_API_KEY",
            chat_model="gpt-4o-mini",
            embed_model="text-embedding-3-small",
        ),
        blob_config=BlobConfig(
            provider="local",
            resources_dir="./data/resources",
        ),
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

    # Add a memory
    result = await service.memorize(
        resource_url="./data/example_conversation.txt",
        modality="conversation",
    )

    print(f"Created {len(result['items'])} memory items")
    print(f"Categories: {[cat['name'] for cat in result['categories']]}\n")

    # Retrieve memories
    queries = [{"role": "user", "content": {"text": "What do you know about me?"}}]
    retrieved = await service.retrieve(queries)

    print(f"Retrieved {len(retrieved['items'])} items")
    print(f"Retrieved {len(retrieved['categories'])} categories")
    print(f"Retrieved {len(retrieved['resources'])} resources\n")


async def example_multi_user():
    """Example: Multiple users with the same agent."""
    print("=== Example 2: Multiple users with the same agent ===\n")

    agent_id = "assistant_v1"

    # User 1
    service1 = MemoryService(
        user_id="alice",
        agent_id=agent_id,
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

    # User 2
    service2 = MemoryService(
        user_id="bob",
        agent_id=agent_id,
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

    print("Each user has their own isolated memory space.")
    print(f"Alice's service: user_id={service1.user_id}, agent_id={service1.agent_id}")
    print(f"Bob's service: user_id={service2.user_id}, agent_id={service2.agent_id}\n")


async def example_multi_agent():
    """Example: Multiple agents for the same user."""
    print("=== Example 3: Multiple agents for the same user ===\n")

    user_id = "charlie"

    # Agent 1 - General assistant
    service_general = MemoryService(
        user_id=user_id,
        agent_id="general_assistant",
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

    # Agent 2 - Specialized coding assistant
    service_coding = MemoryService(
        user_id=user_id,
        agent_id="coding_assistant",
        database_config=DatabaseConfig(
            provider="sqlite",
            sqlite_path="./data/memu.db",
            vector_db_path="./data/vectors.json",
        ),
    )

    print("Each agent has its own memory space for the same user.")
    print(f"General assistant: user_id={service_general.user_id}, agent_id={service_general.agent_id}")
    print(f"Coding assistant: user_id={service_coding.user_id}, agent_id={service_coding.agent_id}\n")


async def example_migration():
    """Example: Database migration and backup."""
    print("=== Example 4: Database migration and backup ===\n")

    # Initialize database schema
    migrate_database(
        db_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
    )
    print("Database schema initialized.\n")

    # Create a backup
    backup_database(
        db_path="./data/memu.db",
        vector_db_path="./data/vectors.json",
        backup_path="./data/backups",
    )
    print("Database backed up.\n")

    # Reset database (use with caution!)
    # reset_database(
    #     db_path="./data/memu.db",
    #     vector_db_path="./data/vectors.json",
    # )
    # print("Database reset.\n")


async def example_in_memory_mode():
    """Example: Using in-memory mode (no persistence)."""
    print("=== Example 5: In-memory mode (no persistence) ===\n")

    service = MemoryService(
        user_id="temp_user",
        agent_id="temp_agent",
        database_config=DatabaseConfig(
            provider="memory",  # Use in-memory storage
        ),
    )

    print("Service using in-memory storage (no persistence)")
    print(f"user_id={service.user_id}, agent_id={service.agent_id}\n")


async def main():
    """Run all examples."""
    print("MemU - User and Agent ID Support Examples\n")
    print("=" * 60 + "\n")

    # Run examples
    # await example_single_user_agent()
    # await example_multi_user()
    await example_multi_agent()
    await example_migration()
    await example_in_memory_mode()

    print("=" * 60)
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
