import os
import json
import time
from typing import List, Dict

from memu import MemuClient


def load_conversations_from_file(file_path: str) -> List[Dict[str, str]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    return conversation


def wait_for_task_completion(memu_client: MemuClient, task_id: str) -> None:
    """Wait for a memorization task to complete."""
    while True:
        status = memu_client.get_task_status(task_id)
        print(f"Task status: {status.status}")
        if status.status in ['SUCCESS', 'FAILURE', 'REVOKED']:
            break
        time.sleep(2)


def main():
    # Initialize MemU client
    memu_client = MemuClient(
        base_url="https://api.memu.so", 
        api_key=os.getenv("MEMU_API_KEY")
    )

    # Load conversation from JSON file
    conversation_file = os.path.join(os.path.dirname(__file__), "conversation.json")
    conversation_messages = load_conversations_from_file(conversation_file)
    
    if not conversation_messages:
        print("No conversation loaded. Exiting.")
        return


    # Save conversation to MemU
    print("\nProcessing multi-turn conversation")
    memo_response = memu_client.memorize_conversation(
        conversation=conversation_messages,
        user_id="user002", 
        user_name="User 002", 
        agent_id="assistant002", 
        agent_name="Assistant 002"
    )
    print(f"Saved! Task ID: {memo_response.task_id}")

    time.sleep(5)
    # Wait for completion
    wait_for_task_completion(memu_client, memo_response.task_id)
    print("Conversation completed successfully!")

    print("\nConversation has been processed and saved to MemU!")

    memories = memu_client.retrieve_related_memory_items(
        user_id="user001", 
        query="hiking safety", 
        top_k=3
    )
    for memory_item in memories.related_memories:
        print(f"Memory: {memory_item.memory.content[:100]}...")

    # Retrieve default categories
    default_categories = memu_client.retrieve_default_categories(
        user_id="user002",
        agent_id="assistant002",
        include_inactive=False
    )
    print(f"Found {default_categories.total_categories} default categories:")
    for category in default_categories.categories:
        print(f"  - {category.name}: {category.description}")

    # Retrieve related clustered categories
    related_categories = memu_client.retrieve_related_clustered_categories(
        user_id="user002",
        category_query="outdoor activities",
        top_k=5,
        min_similarity=0.3
    )

    print(f"Found {len(related_categories.clustered_categories)} related categories:")
    for category in related_categories.clustered_categories:
        print(f"  - {category.name}")

    # Example: Delete memories
    print("\n🗑️ Deleting memories examples:")
    
    # Delete memories for a specific user and agent
    print("Deleting memories for user002 and assistant002...")
    delete_response = memu_client.delete_memories(
        user_id="user002",
        agent_id="assistant002"
    )
    print(f"✅ Success: {delete_response.success}")
    print(f"   Deleted {delete_response.deleted_count} memories")

    # Example: Delete all memories for a user (without specifying agent)
    print("\nDeleting all memories for user002...")
    delete_all_response = memu_client.delete_memories(user_id="user002")
    print(f"✅ Success: {delete_all_response.success}")
    print(f"   Deleted {delete_all_response.deleted_count} memories")

    memu_client.close()


if __name__ == "__main__":
    main()