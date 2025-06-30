"""
PersonaLab Memo Integration Example

Demonstrates how to use both the memory system and the memo module together:
- Memory system for core memory management (profiles, events)
- Memo module for conversation recording and vector search
"""

import json
import time
from personalab.memory import MemoryClient
from personalab.memo import ConversationManager

def main():
    print("=== PersonaLab Memo Integration Example ===\n")
    
    # Initialize both systems
    memory_client = MemoryClient(
        db_path="memory_example.db",
        # Using mock LLM client for demo (no API calls)
        llm_client_type="mock"
    )
    conversation_manager = ConversationManager(
        db_path="conversations_example.db",
        enable_embeddings=True,
        embedding_provider="simple"  # Using simple provider for demo
    )
    
    agent_id = "demo_agent"
    
    # Example conversation 1: Introduction
    print("1. Recording introduction conversation...")
    conversation1 = [
        {"role": "user", "content": "Hi, I'm Alice. I'm 25 years old and I work as a software engineer."},
        {"role": "assistant", "content": "Nice to meet you, Alice! It's great to know you're a software engineer. What kind of projects do you typically work on?"},
        {"role": "user", "content": "I mainly work on web applications using Python and React. I love building user-friendly interfaces."},
        {"role": "assistant", "content": "That sounds really interesting! Python and React are excellent technologies for web development."}
    ]
    
    # Update memory with conversation
    memory, pipeline_result = memory_client.update_memory_with_conversation(agent_id, conversation1)
    print(f"Memory updated: {memory.memory_id}")
    
    # Record conversation in memo system
    recorded_conv1 = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=conversation1,
        memory_id=memory.memory_id
    )
    print(f"Conversation recorded: {recorded_conv1.conversation_id}\n")
    
    # Example conversation 2: Hobby discussion
    print("2. Recording hobby conversation...")
    conversation2 = [
        {"role": "user", "content": "In my free time, I enjoy playing guitar and hiking in the mountains."},
        {"role": "assistant", "content": "Guitar and hiking are wonderful hobbies! How long have you been playing guitar?"},
        {"role": "user", "content": "I've been playing for about 8 years now. I love both acoustic and electric guitar."},
        {"role": "assistant", "content": "That's impressive! Eight years of experience must mean you're quite skilled."}
    ]
    
    # Update memory and record conversation
    memory, pipeline_result = memory_client.update_memory_with_conversation(agent_id, conversation2)
    recorded_conv2 = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=conversation2,
        memory_id=memory.memory_id
    )
    print(f"Second conversation recorded: {recorded_conv2.conversation_id}\n")
    
    # Example conversation 3: Travel discussion
    print("3. Recording travel conversation...")
    conversation3 = [
        {"role": "user", "content": "I recently traveled to Japan and it was amazing. The culture and food were incredible."},
        {"role": "assistant", "content": "Japan sounds like it was a wonderful experience! What was your favorite part of the trip?"},
        {"role": "user", "content": "I loved visiting the temples in Kyoto and trying authentic ramen in Tokyo."},
        {"role": "assistant", "content": "Kyoto temples and Tokyo ramen - you experienced some of the best Japan has to offer!"}
    ]
    
    memory, pipeline_result = memory_client.update_memory_with_conversation(agent_id, conversation3)
    recorded_conv3 = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=conversation3,
        memory_id=memory.memory_id
    )
    print(f"Third conversation recorded: {recorded_conv3.conversation_id}\n")
    
    # Display current memory state
    print("4. Current Memory State:")
    print("Profile Memory:")
    print(memory.get_profile_content())
    print("\nEvent Memory:")
    for event in memory.get_event_content():
        print(f"- {event}")
    print()
    
    # Search for similar conversations
    print("5. Searching similar conversations:")
    
    # Search for music-related conversations
    print("\nSearching for 'music guitar'...")
    music_results = conversation_manager.search_similar_conversations(
        agent_id=agent_id,
        query="music guitar playing",
        limit=5,
        similarity_threshold=0.1
    )
    
    for i, result in enumerate(music_results, 1):
        print(f"  {i}. Score: {result['similarity_score']:.3f}")
        print(f"     Summary: {result['summary']}")
        print(f"     Content: {result['matched_content'][:100]}...")
        print()
    
    # Search for travel-related conversations
    print("Searching for 'travel Japan'...")
    travel_results = conversation_manager.search_similar_conversations(
        agent_id=agent_id,
        query="travel Japan culture",
        limit=5,
        similarity_threshold=0.1
    )
    
    for i, result in enumerate(travel_results, 1):
        print(f"  {i}. Score: {result['similarity_score']:.3f}")
        print(f"     Summary: {result['summary']}")
        print(f"     Content: {result['matched_content'][:100]}...")
        print()
    
    # Get conversation history
    print("6. Conversation History:")
    history = conversation_manager.get_conversation_history(agent_id, limit=10)
    
    for i, conv in enumerate(history, 1):
        print(f"  {i}. ID: {conv['conversation_id'][:8]}...")
        print(f"     Created: {conv['created_at']}")
        print(f"     Turns: {conv['turn_count']}")
        print(f"     Summary: {conv['summary']}")
        print()
    
    # Get conversation statistics
    print("7. Statistics:")
    memory_stats = memory_client.get_memory_stats(agent_id)
    print("Memory Stats:")
    for key, value in memory_stats.items():
        print(f"  {key}: {value}")
    print()
    
    conversation_stats = conversation_manager.get_conversation_stats(agent_id)
    print("Conversation Stats:")
    for key, value in conversation_stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Get detailed conversation
    print("8. Detailed Conversation Example:")
    if history:
        first_conv_id = history[0]['conversation_id']
        detailed_conv = conversation_manager.get_conversation(first_conv_id)
        
        if detailed_conv:
            print(f"Conversation ID: {detailed_conv.conversation_id}")
            print(f"Agent ID: {detailed_conv.agent_id}")
            print(f"Created: {detailed_conv.created_at}")
            print(f"Turn Count: {detailed_conv.turn_count}")
            print(f"Messages:")
            
            for i, message in enumerate(detailed_conv.messages, 1):
                print(f"  {i}. {message.role}: {message.content}")
            print()
    
    print("=== Example completed successfully! ===")
    print("\nThe memo module provides:")
    print("- Conversation recording and storage")
    print("- Vector embeddings for semantic search") 
    print("- Session-based conversation tracking")
    print("- Integration with existing memory system")

if __name__ == "__main__":
    main() 