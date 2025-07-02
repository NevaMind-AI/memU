#!/usr/bin/env python3
"""
PersonaLab Example 01: Quick Start Guide
========================================

This example demonstrates the basic usage of PersonaLab's Persona class.

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys:
   - OPENAI_API_KEY="your-openai-key"
   OR
   - ANTHROPIC_API_KEY="your-anthropic-key"

This is the fastest way to get started with PersonaLab!
"""

import os
from personalab import Persona


def demo_basic_usage():
    """Demonstrate basic Persona usage with new endsession workflow"""
    print("🚀 PersonaLab Quick Start Demo")
    print("=" * 50)
    
    # Check if API keys are available
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))
    
    if not (has_openai or has_anthropic):
        print("❌ No API keys found!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
        print("\nFor demo purposes, we'll use a custom mock LLM instead:")
        
        # Create a simple mock function for demonstration
        def mock_llm_function(messages, **kwargs):
            user_msg = messages[-1]['content'].lower()
            
            if 'hello' in user_msg or 'hi' in user_msg:
                return "Hello! I'm your PersonaLab AI assistant. I have memory capabilities and can learn about you over time."
            elif 'name' in user_msg:
                return "You can call me PersonaLab Assistant. I remember our conversations and can help you with various tasks."
            elif 'remember' in user_msg or 'memory' in user_msg:
                return "Yes, I can remember our conversations! I store important information about you and our interactions."
            elif 'hobby' in user_msg or 'like' in user_msg:
                return "I'll remember your interests and hobbies. This helps me provide more personalized assistance in future conversations."
            else:
                return f"I understand you said: '{messages[-1]['content']}'. I'm storing this in my memory for future reference."
        
        # Use custom LLM function
        from personalab.llm import CustomLLMClient
        custom_client = CustomLLMClient(llm_function=mock_llm_function)
        persona = Persona(
            agent_id="demo_user",
            llm_client=custom_client
        )
        print("✅ Using demo mode with mock LLM\n")
        
    else:
        if has_openai:
            persona = Persona(agent_id="demo_user")  # Default OpenAI
            print("✅ Using OpenAI GPT model\n")
        else:
            from personalab.llm import AnthropicClient
            anthropic_client = AnthropicClient()
            persona = Persona(agent_id="demo_user", llm_client=anthropic_client)
            print("✅ Using Anthropic Claude model\n")
    
    # Demo conversation
    print("🗣️  Starting conversation demo...")
    print("=" * 30)
    
    conversations = [
        "Hello! I'm new to PersonaLab.",
        "My name is Alex and I'm a software developer.",
        "I love Python programming and machine learning.",
        "Do you remember what I told you about my interests?"
    ]
    
    # Show initial session state
    session_info = persona.get_session_info()
    print(f"📊 Initial session: {session_info['pending_conversations']} pending conversations")
    
    for i, msg in enumerate(conversations, 1):
        print(f"\n[Turn {i}]")
        print(f"You: {msg}")
        
        try:
            response = persona.chat(msg)
            print(f"AI: {response}")
            
            # Show session state after each conversation
            session_info = persona.get_session_info()
            print(f"💭 Session buffer: {session_info['pending_conversations']} conversations pending memory update")
            
        except Exception as e:
            print(f"AI: Sorry, I encountered an error: {e}")
            print("This might be due to missing API keys or network issues.")
    
    # Show memory before ending session
    print("\n" + "=" * 50)
    print("🧠 Memory Before Session End:")
    print("=" * 50)
    
    memory_before = persona.get_memory()
    print("📋 Current memory state:")
    for key, values in memory_before.items():
        print(f"  {key}: {len(values)} items")
    
    # End session to update memory
    print("\n🔚 Ending conversation session...")
    result = persona.endsession()
    print(f"✅ Session ended - {result['events']} conversations processed into memory")
    
    # Show what was learned after session end
    print("\n" + "=" * 50)
    print("📝 What PersonaLab Remembered:")
    print("=" * 50)
    
    memory = persona.get_memory()
    
    if memory['events']:
        print("\n🎯 Conversation Events:")
        for i, event in enumerate(memory['events'], 1):
            print(f"  {i}. {event}")
    
    if memory['facts']:
        print("\n📚 Facts:")
        for fact in memory['facts']:
            print(f"  • {fact}")
    
    if memory['preferences']:
        print("\n❤️  Preferences:")
        for pref in memory['preferences']:
            print(f"  • {pref}")
    
    # Demonstrate search (if memo is enabled)
    print("\n" + "=" * 50)
    print("🔍 Search Demo:")
    print("=" * 50)
    
    search_results = persona.search("programming")
    if search_results:
        print("\nFound relevant conversations about 'programming':")
        for i, result in enumerate(search_results[:3], 1):
            print(f"  {i}. {result.get('summary', 'No summary available')}")
    else:
        print("No relevant conversations found (this is normal for new users)")
    
    # Demonstrate multiple sessions
    print("\n" + "=" * 50)
    print("🔄 Multiple Sessions Demo:")
    print("=" * 50)
    
    print("Starting a new conversation session...")
    persona.chat("I also enjoy reading technical books.")
    persona.chat("My favorite programming language is definitely Python.")
    
    session_info = persona.get_session_info()
    print(f"💭 New session: {session_info['pending_conversations']} conversations in buffer")
    
    # Cleanup (auto-endsession)
    print("\n🚪 Closing persona (auto-endsession will be triggered)...")
    persona.close()
    print("✅ Persona closed successfully")
    
    print("\n" + "=" * 50)
    print("✅ Quick Start Demo Complete!")
    print("=" * 50)
    print("\n💡 What you've learned:")
    print("  • How to create a Persona instance")
    print("  • How to have conversations with memory")
    print("  • NEW: Memory updates happen at session end, not during chat")
    print("  • How to manually end sessions with endsession()")
    print("  • How personas auto-save on close()")
    print("  • How to search through conversation history")
    print("\n🎯 Key Workflow Changes:")
    print("  • chat() stores conversations in session buffer")
    print("  • endsession() processes buffer and updates memory")
    print("  • close() automatically calls endsession() if needed")
    print("  • This allows better control over when memory updates occur")
    print("\n🎯 Next steps:")
    print("  • Try example 02 for detailed memory operations")
    print("  • Check example 03 for conversation retrieval features")
    print("  • See example 04 for different feature combinations")


def main():
    """Main function"""
    try:
        demo_basic_usage()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your .env file and API keys.")


if __name__ == "__main__":
    main() 