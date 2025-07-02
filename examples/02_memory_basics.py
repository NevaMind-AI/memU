#!/usr/bin/env python3
"""
PersonaLab Example 02: Memory Basics
====================================

This example demonstrates detailed memory management operations using PersonaLab's Persona class.

You'll learn how to:
- Manage long-term memory (facts, preferences, insights)
- Control memory updates manually
- View and manipulate memory content
- Understand different memory components

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys:
   - OPENAI_API_KEY="your-openai-key"
   OR
   - ANTHROPIC_API_KEY="your-anthropic-key"
"""

import os
from personalab import Persona


def demo_memory_operations():
    """Demonstrate detailed memory operations"""
    print("🧠 PersonaLab Memory Management Demo")
    print("=" * 50)
    
    # Check API availability and create persona
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')):
        print("❌ No API keys found! Using mock LLM for demonstration.")
        
        def mock_llm_function(messages, **kwargs):
            user_msg = messages[-1]['content'].lower()
            if 'python' in user_msg or 'programming' in user_msg:
                return "I see you're interested in Python programming! That's a valuable skill for data science and web development."
            elif 'data science' in user_msg:
                return "Data science is fascinating! It combines programming, statistics, and domain expertise."
            elif 'remember' in user_msg or 'know' in user_msg:
                return "Let me check what I know about you from our previous conversations..."
            else:
                return f"Thank you for sharing that with me. I'll remember this information for our future conversations."
        
        from personalab.llm import CustomLLMClient
        custom_client = CustomLLMClient(llm_function=mock_llm_function)
        persona = Persona(
            agent_id="memory_demo_user",
            llm_client=custom_client,
            use_memory=True,
            use_memo=True
        )
        print("✅ Created persona with mock LLM\n")
    else:
        persona = Persona(
            agent_id="memory_demo_user",
            use_memory=True,
            use_memo=True
        )
        print("✅ Created persona with real LLM\n")
    
    # Step 1: Manual memory management
    print("Step 1: Manual Memory Management")
    print("-" * 40)
    
    # Add facts manually
    print("📚 Adding facts to memory...")
    facts_to_add = [
        "User is a software engineer with 5 years experience",
        "User specializes in Python and machine learning",
        "User works at a tech startup in San Francisco"
    ]
    
    for fact in facts_to_add:
        persona.add_memory(fact, memory_type="facts")
        print(f"  ✅ Added fact: {fact}")
    
    # Add preferences manually
    print("\n❤️  Adding preferences to memory...")
    preferences_to_add = [
        "Prefers hands-on learning over theoretical explanations",
        "Likes practical examples and code snippets",
        "Interested in AI and machine learning applications"
    ]
    
    for pref in preferences_to_add:
        persona.add_memory(pref, memory_type="preferences")
        print(f"  ✅ Added preference: {pref}")
    
    # View current memory state
    print("\n📋 Current memory state:")
    memory = persona.get_memory()
    for key, values in memory.items():
        if values:
            print(f"  {key.upper()}:")
            for i, value in enumerate(values, 1):
                print(f"    {i}. {value}")
    
    # Step 2: Learning through conversation
    print("\n" + "=" * 50)
    print("Step 2: Learning Through Conversation")
    print("-" * 40)
    
    conversations = [
        "I've been learning about deep learning frameworks lately.",
        "TensorFlow and PyTorch are both interesting, but I prefer PyTorch for research.",
        "I'm working on a computer vision project using CNNs.",
        "My goal is to build an image classification system for medical diagnosis."
    ]
    
    for i, msg in enumerate(conversations, 1):
        print(f"\n[Conversation {i}]")
        print(f"You: {msg}")
        
        try:
            # Chat with learning enabled (default)
            response = persona.chat(msg, learn=True)
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
    
    # Step 3: View updated memory
    print("\n" + "=" * 50)
    print("Step 3: Updated Memory After Conversations")
    print("-" * 40)
    
    updated_memory = persona.get_memory()
    
    print("📚 Facts:")
    for i, fact in enumerate(updated_memory.get('facts', []), 1):
        print(f"  {i}. {fact}")
    
    print("\n❤️  Preferences:")
    for i, pref in enumerate(updated_memory.get('preferences', []), 1):
        print(f"  {i}. {pref}")
    
    print("\n🎯 Recent Events:")
    for i, event in enumerate(updated_memory.get('events', []), 1):
        print(f"  {i}. {event}")
    
    # Step 4: Test memory retrieval
    print("\n" + "=" * 50)
    print("Step 4: Testing Memory Retrieval")
    print("-" * 40)
    
    test_questions = [
        "What do you know about my programming experience?",
        "What are my preferences for learning?",
        "What have I told you about deep learning?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n[Memory Test {i}]")
        print(f"You: {question}")
        
        try:
            response = persona.chat(question, learn=False)  # Don't learn from test questions
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
    
    # Step 5: Search functionality
    print("\n" + "=" * 50)
    print("Step 5: Search Functionality")
    print("-" * 40)
    
    search_terms = ["programming", "machine learning", "PyTorch"]
    
    for term in search_terms:
        print(f"\n🔍 Searching for: '{term}'")
        try:
            results = persona.search(term)
            if results:
                print(f"  Found {len(results)} relevant conversations:")
                for i, result in enumerate(results[:2], 1):  # Show top 2
                    summary = result.get('summary', 'No summary available')
                    print(f"    {i}. {summary[:80]}...")
            else:
                print("  No relevant conversations found.")
        except Exception as e:
            print(f"  Search error: {e}")
    
    # Step 6: Memory persistence demo
    print("\n" + "=" * 50)
    print("Step 6: Memory Persistence")
    print("-" * 40)
    
    agent_id = persona.agent_id
    persona.close()
    print("✅ Closed persona instance")
    
    # Create new instance with same agent_id
    if os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'):
        new_persona = Persona(agent_id=agent_id, use_memory=True, use_memo=True)
    else:
        custom_client = CustomLLMClient(llm_function=mock_llm_function)
        new_persona = Persona(
            agent_id=agent_id,
            llm_client=custom_client,
            use_memory=True,
            use_memo=True
        )
    
    print("✅ Created new persona instance with same agent_id")
    
    # Check if memory persisted
    persisted_memory = new_persona.get_memory()
    print("\n📋 Persisted memory:")
    
    if any(persisted_memory.values()):
        for key, values in persisted_memory.items():
            if values:
                print(f"  {key.upper()}: {len(values)} items")
        print("✅ Memory successfully persisted!")
    else:
        print("❌ No memory found (this might be normal in demo mode)")
    
    # Final test with persisted memory
    print("\n💬 Testing with persisted memory:")
    try:
        response = new_persona.chat("Do you remember our previous conversations?", learn=False)
        print(f"AI: {response}")
    except Exception as e:
        print(f"AI: [Error: {e}]")
    
    new_persona.close()
    
    print("\n" + "=" * 50)
    print("✅ Memory Basics Demo Complete!")
    print("=" * 50)
    print("\n💡 What you've learned:")
    print("  • How to manually add facts and preferences to memory")
    print("  • How conversations automatically update memory")
    print("  • How to view and inspect memory contents")
    print("  • How to test memory retrieval")
    print("  • How memory persists across sessions")
    print("\n🎯 Next steps:")
    print("  • Try example 03 for conversation retrieval features")
    print("  • Check example 04 for feature combinations")


def main():
    """Main function"""
    try:
        demo_memory_operations()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 