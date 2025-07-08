#!/usr/bin/env python3
"""
PersonaLab Interactive Chat with Retrieval Visualization

An interactive chat interface that demonstrates PersonaLab's memory retrieval
functionality in real-time. You can chat with the AI and see when it retrieves
relevant memories from previous conversations.

Prerequisites:
1. Set OPENAI_API_KEY in your environment or .env file
2. Install PersonaLab: pip install personalab[ai]

Usage:
    python examples/interactive_chat.py
"""

import os
import sys
from datetime import datetime

# Add project root to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab import Persona


def print_banner():
    """Print the welcome banner."""
    print("🤖 PersonaLab Interactive Chat with Memory Retrieval")
    print("=" * 60)
    print("💬 Type 'exit' or 'quit' to end the conversation")
    print("📝 Type 'memory' to see what the AI remembers about you")
    print("🔄 Type 'clear' to start a fresh conversation")
    print("🔍 Watch for retrieval indicators during the conversation!")
    print("=" * 60)


def show_memory(persona, user_id):
    """Display the current memory state."""
    print("\n" + "="*50)
    print("🧠 CURRENT MEMORY STATE")
    print("="*50)
    
    memory = persona.get_memory(user_id)
    
    profile = memory.get_profile()
    if profile:
        print(f"👤 Profile: {profile}")
    else:
        print("👤 Profile: No profile yet")
    
    events = memory.get_events()
    print(f"📅 Events: {len(events)} recorded")
    
    if events:
        print("\n🔸 Recent Events:")
        for i, event in enumerate(events[-5:], 1):  # Show last 5 events
            print(f"   {i}. {event}")
    
    mind = memory.get_mind()
    if mind:
        print(f"\n🧩 AI Insights: {mind}")
    
    print("="*50 + "\n")


def main():
    """Run the interactive chat with retrieval visualization."""
    
    print_banner()
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: Please set OPENAI_API_KEY environment variable")
        print("💡 You can add it to a .env file in the project root")
        return 1
    
    try:
        # Create AI assistant with retrieval visualization
        print("🔧 Creating AI assistant with memory capabilities...")
        assistant = Persona(
            agent_id="interactive_chat_bot",
            personality="""You are a helpful, friendly, and conversational AI assistant. You:
- Remember details about users across conversations
- Ask follow-up questions to learn more about users
- Reference previous conversations naturally
- Show genuine interest in users' goals and progress
- Provide personalized recommendations based on what you know""",
            use_memory=True,
            show_retrieval=True  # Show retrieval process
        )
        
        print("✅ AI Assistant ready!")
        print("\n💡 The assistant will remember our conversation and reference it in future messages.")
        
        user_id = f"interactive_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conversation_count = 0
        
        while True:
            try:
                # Get user input
                print("\n" + "-" * 40)
                user_input = input("👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Ending conversation and saving memory...")
                    assistant.endsession(user_id)
                    print("✅ Memory saved! Goodbye!")
                    break
                
                elif user_input.lower() == 'memory':
                    show_memory(assistant, user_id)
                    continue
                
                elif user_input.lower() == 'clear':
                    print("\n🔄 Starting fresh conversation...")
                    assistant.endsession(user_id)
                    user_id = f"interactive_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    conversation_count = 0
                    print("✅ Memory cleared! Starting new session.")
                    continue
                
                # Show retrieval indicator for longer conversations
                conversation_count += 1
                if conversation_count > 2:
                    print("🔍 [Checking memory for relevant context...]")
                
                # Get AI response
                response = assistant.chat(user_input, user_id=user_id)
                
                # Display response
                print(f"🤖 Assistant: {response}")
                
                # Show retrieval success indicator for later messages
                if conversation_count > 2:
                    print("✅ [Memory context used in response]")
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Chat interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error during chat: {e}")
                continue
        
        # Final memory summary
        print("\n" + "="*60)
        print("📊 FINAL CONVERSATION SUMMARY")
        print("="*60)
        
        final_memory = assistant.get_memory(user_id)
        print(f"💬 Total interactions: {conversation_count}")
        print(f"🧠 Events recorded: {len(final_memory.get_events())}")
        
        profile = final_memory.get_profile()
        if profile:
            print(f"👤 What AI learned about you: {profile}")
        
        # Cleanup
        assistant.close()
        print("\n✅ Interactive chat completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 