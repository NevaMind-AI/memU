"""
OpenAI Chat + MemU SDK Example
============================

5-round chat with OpenAI → Summary → Test 3 retrieve APIs
"""

import os
import sys
import time
from pathlib import Path

# Add memu package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import openai
from memu.sdk import MemuClient

# Set your API keys
openai_api_key = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
memu_api_key = os.getenv("MEMU_API_KEY", "your-memu-key-here")

# Initialize clients
openai_client = openai.OpenAI(api_key=openai_api_key)
memu_client = MemuClient(
    base_url="https://api-preview.memu.so",
    api_key=memu_api_key
)

print("🤖 Starting 5-round chat with OpenAI...")

# Pre-defined questions for 5 rounds
questions = [
    "I love hiking in the mountains and exploring nature trails",
    "Tell me about the benefits of outdoor activities for mental health",
    "What equipment do I need for a day hike in rocky terrain?",
    "How do I prepare for altitude changes during mountain hiking?",
    "What are some safety tips for solo hiking adventures?"
]

# Store all conversations
all_conversations = []
messages_history = [{"role": "system", "content": "You are a helpful assistant about outdoor activities and hiking."}]

# 5 rounds of chat
for i, question in enumerate(questions, 1):
    print(f"\n🏔️ Round {i}:")
    print(f"User: {question}")
    
    messages_history.append({"role": "user", "content": question})
    
    # Chat with OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages_history,
        max_tokens=200
    )
    
    assistant_response = response.choices[0].message.content
    print(f"Assistant: {assistant_response}")
    
    messages_history.append({"role": "assistant", "content": assistant_response})
    all_conversations.append(f"user: {question}\n\nassistant: {assistant_response}")

    
# Save to MemU
response = memu_client.memorize_conversation(
    conversation_text='\n\n'.join(all_conversations),
    user_id="demo_user",
    user_name="Demo User", 
    agent_id="openai_gpt",
    agent_name="OpenAI Assistant"
)

task_id = response.task_id
print(f"💾 Conversation saved! Task ID: {task_id}")

# Wait for task to finish
print("⏳ Waiting for memorization task to complete...")
while True:
    status = memu_client.get_task_status(task_id)
    print(f"📊 Task status: {status.status}")
    
    if status.status in ['SUCCESS', 'FAILURE', 'REVOKED']:
        print(f"✅ Task completed with status: {status.status}")
        break
        
    time.sleep(3)

# Test 3 retrieve APIs
print("\n🧠 Testing 3 retrieve SDK APIs...")

# API 1: retrieve_default_categories
print("\n1️⃣ Testing retrieve_default_categories")
try:
    categories = memu_client.retrieve_default_categories(
        user_id="demo_user",
        agent_id="openai_gpt"
    )
    print(f"✅ Found {categories.total_categories} categories")
    for i, cat in enumerate(categories.categories[:3]):
        print(f"   {i+1}. {list(cat.keys())[:2]}")
except Exception as e:
    print(f"❌ Error: {e}")

# API 2: retrieve_related_clustered_categories  
print("\n2️⃣ Testing retrieve_related_clustered_categories")
try:
    clustered = memu_client.retrieve_related_clustered_categories(
        user_id="demo_user",
        category_query="hiking outdoor mountain activities",
        top_k=3
    )
    print(f"✅ Found {clustered.total_categories_found} clustered categories")
    for i, cluster in enumerate(clustered.clustered_categories):
        print(f"   {i+1}. {cluster.category_name}: {cluster.similarity_score:.3f}")
except Exception as e:
    print(f"❌ Error: {e}")

# API 3: retrieve_related_memory_items
print("\n3️⃣ Testing retrieve_related_memory_items")  
try:
    memories = memu_client.retrieve_related_memory_items(
        user_id="demo_user",
        query="hiking safety equipment mountain",
        top_k=5
    )
    print(f"✅ Found {memories.total_found} related memories")
    for i, mem in enumerate(memories.related_memories[:3]):
        print(f"   {i+1}. {mem.memory.category}: {mem.similarity_score:.3f}")
        print(f"      {mem.memory.content[:100]}...")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🎉 All tests completed!")
memu_client.close()