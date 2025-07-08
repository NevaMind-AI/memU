#!/usr/bin/env python3
"""
PersonaLab Quick Start Chat Example

A minimal example showing how to get started with PersonaLab Persona chat.

Prerequisites:
1. Set OPENAI_API_KEY in your environment or .env file
2. Install PersonaLab: pip install personalab[ai]

Usage:
    python examples/quick_start_chat.py
"""

import os
import sys

# Add project root to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab import Persona


def main():
    """Simple chat example with PersonaLab."""
    
    print("🚀 PersonaLab Quick Start Chat")
    print("=" * 40)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: Please set OPENAI_API_KEY environment variable")
        print("💡 You can add it to a .env file in the project root")
        return 1
    
    try:
        # Create a simple AI assistant
        assistant = Persona(
            agent_id="my_assistant",
            personality="You are a helpful and friendly AI assistant.",
            use_memory=True,
            show_retrieval=True  # Show when memory is being retrieved
        )
        
        print("✅ AI Assistant created!")
        print("💬 Starting conversation...")
        print("-" * 40)
        
        # Example conversation
        user_id = "user_123"
        
        # First message
        print("\n👤 User: Hi! What can you help me with?")
        response1 = assistant.chat("Hi! What can you help me with?", user_id=user_id)
        print(f"🤖 Assistant: {response1}")
        
        # Second message
        print("\n👤 User: I'm learning Python programming. Any tips?")
        response2 = assistant.chat("I'm learning Python programming. Any tips?", user_id=user_id)
        print(f"🤖 Assistant: {response2}")
        
        # Third message - this should trigger memory retrieval
        print("\n👤 User: Can you remember what I told you about learning Python?")
        print("🔍 [PersonaLab is searching memory for relevant context...]")
        response3 = assistant.chat("Can you remember what I told you about learning Python?", user_id=user_id)
        print(f"🤖 Assistant: {response3}")
        
        # Fourth message - test retrieval again
        print("\n👤 User: What programming tips can you give me based on our conversation?")
        print("🔍 [PersonaLab is retrieving previous conversation context...]")
        response4 = assistant.chat("What programming tips can you give me based on our conversation?", user_id=user_id)
        print(f"🤖 Assistant: {response4}")
        
        # End session to save memory
        assistant.endsession(user_id)
        
        print("\n" + "=" * 40)
        print("✅ Chat completed successfully!")
        print("🧠 Conversation has been saved to memory")
        print("🔍 Memory retrieval was demonstrated in responses")
        
        # Show memory info
        memory = assistant.get_memory(user_id)
        print(f"\n📊 Memory Summary:")
        profile = memory.get_profile()
        print(f"   Profile: {profile if profile else 'No profile yet'}")
        events = memory.get_events()
        print(f"   Events: {len(events)} events recorded")
        
        # Cleanup
        assistant.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 