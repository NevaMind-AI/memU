#!/usr/bin/env python3
"""
PersonaLab Example 07: OpenAI Integration & Feature Selection Demo
=================================================================

Demonstrates PersonaLab integration with OpenAI API, including:
- Usage of use_memory and use_memo parameters
- Effects of different feature combinations
- Flexible interactive experience

Before running, ensure:
1. Install PersonaLab: pip install -e .
2. Create .env file and set API key:
   - OPENAI_API_KEY="your-openai-key"
3. Run script: python examples/07_openai_chatbot_integration.py
"""

from personalab import Persona

def demo_full_features():
    """Demonstrate full features (Memory + Memo)"""
    print("=" * 60)
    print("Demo 1: Full Features (Memory + Memo)")
    print("=" * 60)
    
    # Enable all features
    persona = Persona(
        agent_id="alice", 
        use_memory=True,
        use_memo=True,
        show_retrieval=True
    )
    
    # Conversation demo
    test_messages = [
        "I love hiking and photography",
        "I am a software engineer",
        "Do you know my hobbies?"
    ]
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = persona.chat(msg)
        print(f"AI: {response}")
    
    # View memory
    print("\n📝 Recorded memories:")
    memory = persona.get_memory()
    for key, values in memory.items():
        if values:
            print(f"  {key}: {values}")
    
    persona.close()
    print()

def demo_memory_only():
    """Demonstrate Memory-only functionality (no conversation recording)"""
    print("=" * 60)
    print("Demo 2: Memory Only (no conversation recording and retrieval)")
    print("=" * 60)
    
    # Enable Memory functionality only
    persona = Persona(
        agent_id="bob", 
        use_memory=True,
        use_memo=False
    )
    
    # Conversation demo
    test_messages = [
        "I am a data scientist",
        "I love machine learning",
        "Do you remember my profession?"
    ]
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = persona.chat(msg)
        print(f"AI: {response}")
    
    # Try search (will show warning)
    print("\n🔍 Attempting search:")
    results = persona.search("machine learning")
    
    persona.close()
    print()

def demo_memo_only():
    """Demonstrate Memo-only functionality (no long-term memory)"""
    print("=" * 60)
    print("Demo 3: Memo Only (retrieval enabled but no long-term memory)")
    print("=" * 60)
    
    # Enable Memo functionality only
    persona = Persona(
        agent_id="charlie", 
        use_memory=False,
        use_memo=True,
        show_retrieval=True
    )
    
    # Conversation demo
    test_messages = [
        "I am learning Python programming",
        "Django framework is very interesting",
        "Do you know what I'm studying?"
    ]
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = persona.chat(msg)
        print(f"AI: {response}")
    
    # Try to get memory (will show warning)
    print("\n📝 Attempting to get memory:")
    memory = persona.get_memory()
    
    persona.close()
    print()

def demo_minimal():
    """Demonstrate minimal functionality (pure conversation)"""
    print("=" * 60)
    print("Demo 4: Minimal Functionality (pure LLM conversation, no memory)")
    print("=" * 60)
    
    # Disable all advanced features
    persona = Persona(
        agent_id="diana", 
        use_memory=False,
        use_memo=False
    )
    
    # Conversation demo
    test_messages = [
        "I am a doctor",
        "I love reading medical journals",
        "Do you know my profession?"  # Should not remember
    ]
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = persona.chat(msg, learn=False)  # Explicitly no learning
        print(f"AI: {response}")
    
    persona.close()
    print()

def interactive_chat():
    """Interactive chat"""
    print("=" * 60)
    print("Interactive Chat (choose feature combination)")
    print("=" * 60)
    
    print("Choose feature combination:")
    print("1. Full Features (Memory + Memo)")
    print("2. Memory Only")
    print("3. Retrieval Only (Memo only)")
    print("4. Minimal Functionality (pure conversation)")
    
    choice = input("Please choose (1-4): ").strip()
    
    if choice == "1":
        persona = Persona(agent_id="user", use_memory=True, use_memo=True, show_retrieval=True)
        print("🧠 Enabled: Memory + Memo")
    elif choice == "2":
        persona = Persona(agent_id="user", use_memory=True, use_memo=False)
        print("🧠 Enabled: Memory only")
    elif choice == "3":
        persona = Persona(agent_id="user", use_memory=False, use_memo=True, show_retrieval=True)
        print("🧠 Enabled: Memo only")
    elif choice == "4":
        persona = Persona(agent_id="user", use_memory=False, use_memo=False)
        print("🧠 Enabled: Minimal functionality")
    else:
        print("Invalid choice, using default full features")
        persona = Persona(agent_id="user", use_memory=True, use_memo=True, show_retrieval=True)
    
    print("\n🤖 PersonaLab ChatBot (type 'quit' to exit, 'memory' to view memory)")
    print("=" * 50)
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
        elif user_input.lower() == 'memory':
            memory = persona.get_memory()
            print("📝 Current memory:")
            for key, values in memory.items():
                print(f"  {key}: {values}")
            continue
        
        if not user_input:
            continue
        
        try:
            response = persona.chat(user_input)
            print(f"AI: {response}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    persona.close()
    print("\nGoodbye! 👋")

def main():
    """Main function"""
    print("PersonaLab Memory & Memo Feature Demonstration")
    print("=" * 60)
    
    print("Choose demo mode:")
    print("1. Automatic demo of all features")
    print("2. Interactive chat")
    
    mode = input("Please choose (1-2): ").strip()
    
    if mode == "2":
        interactive_chat()
    else:
        demo_full_features()
        demo_memory_only()
        demo_memo_only()
        demo_minimal()
        
        print("=" * 60)
        print("All demos completed!")
        print("=" * 60)

if __name__ == "__main__":
    main() 