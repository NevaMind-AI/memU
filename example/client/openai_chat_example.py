import os
import time

import openai
from memu import MemuClient


def main():
    # Initialize clients
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    memu_client = MemuClient(
        base_url="https://api-preview.memu.so", 
        api_key=os.getenv("MEMU_API_KEY")
    )

    # Single conversation
    question = "I love hiking in mountains. Any safety tips?"
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": question}], 
        max_tokens=150
    )
    answer = response.choices[0].message.content
    print(f"Q: {question}\nA: {answer}")

    # Save to MemU
    memo_response = memu_client.memorize_conversation(
        conversation_text=f"user: {question}\n\nassistant: {answer}",
        user_id="demo_user", 
        user_name="Demo User", 
        agent_id="gpt", 
        agent_name="GPT Assistant"
    )
    print(f"💾 Saved! Task ID: {memo_response.task_id}")

    # Wait for completion
    while True:
        status = memu_client.get_task_status(memo_response.task_id)
        print(f"Task status: {status.status}")
        if status.status in ['SUCCESS', 'FAILURE', 'REVOKED']:
            break
        time.sleep(2)

    # Test recall
    memories = memu_client.retrieve_related_memory_items(
        user_id="demo_user", 
        query="hiking safety", 
        top_k=3
    )
    print(f"🧠 Found {memories.total_found} memories")
    for memory_item in memories.related_memories:
        print(f"Memory: {memory_item.memory.content[:100]}...")
    memu_client.close()


if __name__ == "__main__":
    main()