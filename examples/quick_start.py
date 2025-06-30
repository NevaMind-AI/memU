#!/usr/bin/env python3
"""
PersonaLab + OpenAI Quick Start Example

The simplest possible example showing how to use PersonaLab memory
with OpenAI ChatGPT API in just a few lines of code.

Usage:
    python quick_start.py
"""

import os
from openai import OpenAI
from personalab.utils import enhance_system_prompt_with_memory
from personalab.memory import MemoryClient
from personalab.memo import ConversationManager


def main():
    """Quick start example - minimal code to get started."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key'")
        return
    
    print("🚀 PersonaLab + OpenAI Quick Start")
    print("=" * 40)
    
    # 1. Initialize PersonaLab memory and conversation recording
    memory_client = MemoryClient("quickstart.db")
    conversation_manager = ConversationManager(
        db_path="quickstart_conversations.db",
        enable_embeddings=True,
        embedding_provider="simple"
    )
    agent_id = "quickstart_user"
    
    # 2. Add some user information
    memory_client.update_profile(
        agent_id, 
        "User is a software developer interested in Python and AI"
    )
    memory_client.update_events(agent_id, [
        "Asked about machine learning libraries",
        "Discussed Python best practices"
    ])
    
    # 3. Get memory for the user
    memory = memory_client.get_memory_by_agent(agent_id)
    
    # 4. Create enhanced system prompt
    base_prompt = "You are a helpful coding assistant."
    enhanced_prompt = enhance_system_prompt_with_memory(
        base_system_prompt=base_prompt,
        memory=memory
    )
    
    print("📝 Enhanced System Prompt:")
    print("-" * 40)
    print(enhanced_prompt)
    print("-" * 40)
    
    # 5. Use with OpenAI
    client = OpenAI()
    user_message = "What Python libraries should I learn for machine learning?"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=200
    )
    
    print(f"\n💬 User: {user_message}")
    print(f"🤖 Assistant: {response.choices[0].message.content}")
    
    # 6. Update memory with multi-turn conversation
    # The update_memory_with_conversation method accepts List[Dict[str, str]] where:
    # - Each dict represents one conversation turn with 'role' and 'content' keys
    # - You can pass entire conversation histories or individual exchanges
    # - The method processes all turns together for better context understanding
    multi_turn_conversation = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response.choices[0].message.content},
        {"role": "user", "content": "I'm particularly interested in deep learning. Any specific recommendations?"},
        {"role": "assistant", "content": "For deep learning, I'd recommend starting with TensorFlow or PyTorch. TensorFlow has excellent documentation and Keras integration, while PyTorch is popular in research for its dynamic computation graphs."},
        {"role": "user", "content": "Thanks! I'll start with TensorFlow since I prefer good documentation."}
    ]
    
    # Update memory with conversation
    updated_memory, result = memory_client.update_memory_with_conversation(
        agent_id, 
        multi_turn_conversation
    )
    
    # Record conversation in memo system for vectorization and search
    recorded_conversation = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=multi_turn_conversation,
        memory_id=updated_memory.memory_id
    )
    
    print(f"\n💾 Memory updated from multi-turn conversation: {result.update_result.profile_updated}")
    print(f"📝 Conversation recorded: {recorded_conversation.conversation_id}")
    print("✅ Quick start completed!")
    
    # 7. Demonstrate memo module: conversation recording and vector search
    print("\n" + "="*50)
    print("🆕 Memo Module: Conversation Recording & Vector Search")
    print("="*50)
    
    # Search for similar conversations (if any exist)
    print(f"\n🔍 Searching for conversations about 'machine learning'...")
    similar_conversations = conversation_manager.search_similar_conversations(
        agent_id, 
        "machine learning and AI frameworks",
        limit=3
    )
    
    if similar_conversations:
        print(f"Found {len(similar_conversations)} similar conversations:")
        for i, conv in enumerate(similar_conversations, 1):
            print(f"  {i}. Similarity: {conv['similarity_score']:.3f}")
            print(f"     Summary: {conv['summary']}")
    else:
        print("No similar conversations found (expected for first run)")
    
    # Show conversation history
    print(f"\n📜 Recent conversation history for {agent_id}:")
    history = conversation_manager.get_conversation_history(agent_id, limit=3)
    for i, conv in enumerate(history, 1):
        print(f"  {i}. {conv['created_at'][:19]} - Turns: {conv['turn_count']}")
        print(f"     Summary: {conv['summary']}")
    
    # Display embedding info if available
    if conversation_manager.embedding_manager:
        print(f"\n⚡ Embedding Provider: {conversation_manager.embedding_manager.model_name}")
        print(f"   Vector Dimension: {conversation_manager.embedding_manager.embedding_dimension}")
    
    print("\n💡 Memo Module Features:")
    print("   • Separate conversation recording system (memo module)")
    print("   • Vector embeddings for semantic similarity search")
    print("   • Conversation history tracking by session")
    print("   • Multiple embedding provider support (OpenAI, Sentence Transformers, Simple)")
    print("   • Clean separation: memory system for profiles/events, memo for conversations")
    
    print("\n✅ Enhanced quick start completed with memo module integration!")


if __name__ == "__main__":
    main() 