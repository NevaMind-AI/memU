#!/usr/bin/env python3
"""
PersonaLab Example 04: Feature Combinations
===========================================

This example demonstrates different combinations of PersonaLab features and their effects.

You'll learn how to:
- Use different combinations of use_memory and use_memo
- Understand the performance implications
- Choose the right configuration for your use case
- Compare behavior across different setups

Feature Combinations:
1. Full Features (Memory + Memo) - Best user experience
2. Memory Only - Fast, with long-term learning
3. Memo Only - Fast, with conversation context
4. Minimal - Fastest, pure LLM conversation

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys:
   - OPENAI_API_KEY="your-openai-key"
   OR
   - ANTHROPIC_API_KEY="your-anthropic-key"
"""

import os
import time
from personalab import Persona


def demo_full_features():
    """Demo: Full Features (Memory + Memo)"""
    print("🧠 Configuration 1: Full Features (Memory + Memo)")
    print("=" * 60)
    print("✅ use_memory=True, use_memo=True")
    print("📊 Features: Long-term memory + Conversation retrieval")
    print("⚡ Performance: Moderate (2 LLM calls per conversation)")
    print("🎯 Best for: Rich user experience, personalized AI")
    print()
    
    # Create mock LLM for consistent demo
    def mock_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        if 'remember' in user_msg or 'know' in user_msg:
            return "Yes! I can remember your preferences and retrieve our previous conversations. This gives me rich context about you."
        elif 'project' in user_msg:
            return "I'll remember this project in my long-term memory and also record our conversation for future retrieval."
        else:
            return f"I'm learning about you and storing both facts and conversation history for better future interactions."
    
    from personalab.llm import CustomLLMClient
    custom_client = CustomLLMClient(llm_function=mock_llm_function)
    persona = Persona(
        agent_id="full_user",
        llm_client=custom_client,
        use_memory=True,
        use_memo=True,
        show_retrieval=True
    )
    
    # Test conversations
    conversations = [
        "I'm a data scientist working on NLP projects.",
        "I prefer PyTorch over TensorFlow for deep learning.",
        "What do you remember about my work and preferences?"
    ]
    
    for i, msg in enumerate(conversations, 1):
        print(f"[{i}] You: {msg}")
        response = persona.chat(msg)
        print(f"[{i}] AI: {response}\n")
    
    # Show memory state
    memory = persona.get_memory()
    print("📋 Memory State:")
    for key, values in memory.items():
        if values:
            print(f"  {key}: {len(values)} items")
    
    # Show search capability
    results = persona.search("data science")
    print(f"🔍 Search Results: {len(results)} conversations found")
    
    persona.close()
    print("\n" + "=" * 60 + "\n")


def demo_memory_only():
    """Demo: Memory Only"""
    print("🧠 Configuration 2: Memory Only")
    print("=" * 60)
    print("✅ use_memory=True, use_memo=False")
    print("📊 Features: Long-term memory only")
    print("⚡ Performance: Fast (1 LLM call per conversation)")
    print("🎯 Best for: Learning agent without conversation storage")
    print()
    
    def mock_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        if 'remember' in user_msg or 'know' in user_msg:
            return "I can remember facts about you, but I don't store full conversation history for retrieval."
        elif 'project' in user_msg:
            return "I'll remember the important facts about this project in my long-term memory."
        else:
            return f"I'm learning facts about you for better future interactions."
    
    memory_client = CustomLLMClient(llm_function=mock_llm_function)
    persona = Persona(
        agent_id="memory_user",
        llm_client=memory_client,
        use_memory=True,
        use_memo=False
    )
    
    conversations = [
        "I'm a software engineer specializing in backend development.",
        "I have 5 years of experience with Python and Go.",
        "What facts do you know about me?"
    ]
    
    for i, msg in enumerate(conversations, 1):
        print(f"[{i}] You: {msg}")
        response = persona.chat(msg)
        print(f"[{i}] AI: {response}\n")
    
    # Show memory (should have facts)
    memory = persona.get_memory()
    print("📋 Memory State:")
    for key, values in memory.items():
        if values:
            print(f"  {key}: {len(values)} items")
    
    # Try search (should show warning)
    print("\n🔍 Search Test:")
    try:
        results = persona.search("software")
        print(f"Search Results: {len(results)} found")
    except Exception as e:
        print(f"Search unavailable: {e}")
    
    persona.close()
    print("\n" + "=" * 60 + "\n")


def demo_memo_only():
    """Demo: Memo Only (Conversation Retrieval)"""
    print("🧠 Configuration 3: Memo Only (Conversation Retrieval)")
    print("=" * 60)
    print("✅ use_memory=False, use_memo=True")
    print("📊 Features: Conversation storage and retrieval only")
    print("⚡ Performance: Fast (1 LLM call per conversation)")
    print("🎯 Best for: Context-aware chat without long-term learning")
    print()
    
    def mock_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        if 'remember' in user_msg or 'know' in user_msg:
            return "I can recall our previous conversations, but I don't build long-term memory about you."
        elif 'project' in user_msg:
            return "I'll record this conversation for future reference and context."
        else:
            return f"I'm storing our conversation for better context in future chats."
    
    memo_client = CustomLLMClient(llm_function=mock_llm_function)
    persona = Persona(
        agent_id="memo_user",
        llm_client=memo_client,
        use_memory=False,
        use_memo=True,
        show_retrieval=True
    )
    
    conversations = [
        "I'm working on a mobile app using React Native.",
        "The app is for fitness tracking and meal planning.",
        "Can you recall what I told you about my project?"
    ]
    
    for i, msg in enumerate(conversations, 1):
        print(f"[{i}] You: {msg}")
        response = persona.chat(msg)
        print(f"[{i}] AI: {response}\n")
    
    # Try memory (should show warning)
    print("📋 Memory Test:")
    try:
        memory = persona.get_memory()
        has_memory = any(memory.values())
        print(f"Memory available: {has_memory}")
    except Exception as e:
        print(f"Memory unavailable: {e}")
    
    # Show search capability
    results = persona.search("React Native")
    print(f"🔍 Search Results: {len(results)} conversations found")
    
    persona.close()
    print("\n" + "=" * 60 + "\n")


def demo_minimal():
    """Demo: Minimal (Pure LLM)"""
    print("🧠 Configuration 4: Minimal (Pure LLM)")
    print("=" * 60)
    print("✅ use_memory=False, use_memo=False")
    print("📊 Features: Pure LLM conversation only")
    print("⚡ Performance: Fastest (1 LLM call, no storage)")
    print("🎯 Best for: Simple chatbot, stateless interactions")
    print()
    
    def mock_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        if 'remember' in user_msg or 'know' in user_msg:
            return "I'm a stateless AI - I don't remember our previous conversations or build memory about you."
        elif 'project' in user_msg:
            return "That sounds interesting! However, I won't remember this in future conversations."
        else:
            return f"I'm here to help with your current question, but I don't store any information about our chat."
    
    minimal_client = CustomLLMClient(llm_function=mock_llm_function)
    persona = Persona(
        agent_id="minimal_user",
        llm_client=minimal_client,
        use_memory=False,
        use_memo=False
    )
    
    conversations = [
        "I'm a teacher who loves creative writing.",
        "I write short stories in my spare time.",
        "Do you remember what I told you about myself?"
    ]
    
    for i, msg in enumerate(conversations, 1):
        print(f"[{i}] You: {msg}")
        response = persona.chat(msg, learn=False)  # No learning in minimal mode
        print(f"[{i}] AI: {response}\n")
    
    # Try memory and search (should show warnings)
    print("📋 Memory Test:")
    try:
        memory = persona.get_memory()
        has_memory = any(memory.values())
        print(f"Memory available: {has_memory}")
    except Exception as e:
        print(f"Memory unavailable: {e}")
    
    print("\n🔍 Search Test:")
    try:
        results = persona.search("writing")
        print(f"Search Results: {len(results)} found")
    except Exception as e:
        print(f"Search unavailable: {e}")
    
    persona.close()
    print("\n" + "=" * 60 + "\n")


def performance_comparison():
    """Compare performance characteristics"""
    print("⚡ Performance Comparison")
    print("=" * 60)
    
    configurations = [
        ("Full Features", "2 LLM calls", "Rich experience", "High memory usage"),
        ("Memory Only", "1 LLM call", "Learning enabled", "Medium memory usage"),
        ("Memo Only", "1 LLM call", "Context retrieval", "Medium memory usage"), 
        ("Minimal", "1 LLM call", "Stateless", "Low memory usage")
    ]
    
    print("Configuration    | LLM Calls | Benefits        | Memory Usage")
    print("-" * 60)
    for config, calls, benefit, memory in configurations:
        print(f"{config:<15} | {calls:<9} | {benefit:<15} | {memory}")
    
    print("\n🎯 Choosing the Right Configuration:")
    print("=" * 60)
    print("🚀 Full Features: Production chatbots, personal assistants")
    print("🧠 Memory Only: Learning agents, skill assessment systems") 
    print("💬 Memo Only: Customer support, context-aware help systems")
    print("⚡ Minimal: Simple Q&A, stateless interactions, batch processing")
    print()


def interactive_demo():
    """Interactive comparison demo"""
    print("🎮 Interactive Comparison Demo")
    print("=" * 60)
    print("Choose a configuration to test:")
    print("1. Full Features (Memory + Memo)")
    print("2. Memory Only")
    print("3. Memo Only") 
    print("4. Minimal")
    print("0. Skip interactive demo")
    
    choice = input("\nEnter your choice (0-4): ").strip()
    
    if choice == "0":
        print("Skipping interactive demo.")
        return
    
    # Create persona based on choice
    def mock_llm_function(messages, **kwargs):
        return f"This is a response from configuration {choice}. I'm demonstrating the selected feature set."
    
    config_map = {
        "1": {"use_memory": True, "use_memo": True, "name": "Full Features"},
        "2": {"use_memory": True, "use_memo": False, "name": "Memory Only"},
        "3": {"use_memory": False, "use_memo": True, "name": "Memo Only"},
        "4": {"use_memory": False, "use_memo": False, "name": "Minimal"}
    }
    
    if choice in config_map:
        config = config_map[choice]
        interactive_client = CustomLLMClient(llm_function=mock_llm_function)
        persona = Persona(
            agent_id="interactive_user",
            llm_client=interactive_client,
            **{k: v for k, v in config.items() if k != "name"}
        )
        
        print(f"\n✅ Created persona with {config['name']} configuration")
        print("Type 'quit' to exit, 'memory' to check memory, 'search <term>' to search")
        print("-" * 60)
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'memory':
                try:
                    memory = persona.get_memory()
                    print("📋 Memory:", {k: len(v) for k, v in memory.items() if v})
                except Exception as e:
                    print(f"Memory error: {e}")
            elif user_input.lower().startswith('search '):
                term = user_input[7:]
                try:
                    results = persona.search(term)
                    print(f"🔍 Found {len(results)} results for '{term}'")
                except Exception as e:
                    print(f"Search error: {e}")
            elif user_input:
                try:
                    response = persona.chat(user_input)
                    print(f"AI: {response}")
                except Exception as e:
                    print(f"Chat error: {e}")
        
        persona.close()
        print("✅ Demo completed!")
    else:
        print("Invalid choice. Skipping interactive demo.")


def main():
    """Main function"""
    print("🎛️  PersonaLab Feature Combinations Demo")
    print("=" * 60)
    print("This demo shows different PersonaLab configurations and their trade-offs.\n")
    
    try:
        # Run all configuration demos
        demo_full_features()
        demo_memory_only()
        demo_memo_only()
        demo_minimal()
        
        # Show performance comparison
        performance_comparison()
        
        # Interactive demo
        interactive_demo()
        
        print("\n✅ Feature Combinations Demo Complete!")
        print("=" * 60)
        print("\n💡 Key Takeaways:")
        print("  • Full features provide the richest user experience")
        print("  • Memory-only is great for learning without conversation storage")
        print("  • Memo-only provides context without long-term memory")
        print("  • Minimal mode is fastest for simple, stateless interactions")
        print("\n🎯 Choose based on your use case:")
        print("  • User experience priority → Full Features")
        print("  • Learning priority → Memory Only")
        print("  • Context priority → Memo Only") 
        print("  • Performance priority → Minimal")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 