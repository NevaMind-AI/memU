#!/usr/bin/env python3
"""
PersonaLab Persona Chat Example

Demonstrates the core features of PersonaLab's Persona system:
- Basic chat functionality
- Memory management and persistence
- Multi-user conversations
- Session management
- Historical context retrieval

Prerequisites:
1. Set up environment variables (see .env.example)
2. Configure PostgreSQL database
3. Install PersonaLab: pip install personalab[ai]

Usage:
    python examples/persona_chat_example.py
"""

import os
import sys
from datetime import datetime
from typing import Optional

# Add project root to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab import Persona
from personalab.llm import OpenAIClient


def format_profile_display(profile, max_length=100):
    """
    Safely format profile data for display.
    
    Args:
        profile: Profile data (can be list, string, or None)
        max_length: Maximum length for display
        
    Returns:
        str: Formatted profile string
    """
    if not profile:
        return "No profile"
    
    if isinstance(profile, list):
        profile_str = "\n   ".join(str(item) for item in profile)
    else:
        profile_str = str(profile)
    
    if len(profile_str) > max_length:
        return profile_str[:max_length] + "..."
    else:
        return profile_str


def create_ai_tutor() -> Optional[Persona]:
    """
    Create an AI tutor persona with memory capabilities.
    
    Returns:
        Persona: Configured AI tutor or None if setup fails
    """
    try:
        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ Error: OPENAI_API_KEY not found in environment variables")
            print("💡 Please set your OpenAI API key in .env file")
            return None

        # Create LLM client
        llm_client = OpenAIClient(
            api_key=api_key,
            model="gpt-4o-mini"
        )

        # Create persona with personality and memory
        persona = Persona(
            agent_id="ai_tutor",
            llm_client=llm_client,
            personality="""You are a helpful and patient AI tutor. You:
- Explain concepts clearly and simply
- Ask follow-up questions to check understanding
- Remember what the student has learned
- Adapt your teaching style to each student
- Encourage and motivate students""",
            use_memory=True,  # Enable long-term memory
            show_retrieval=True  # Show when using historical context
        )

        print("✅ AI Tutor created successfully!")
        return persona

    except Exception as e:
        print(f"❌ Error creating AI tutor: {e}")
        return None


def basic_chat_example(persona: Persona):
    """
    Demonstrate basic chat functionality.
    
    Args:
        persona: The AI persona to chat with
    """
    print("\n" + "="*60)
    print("🎯 BASIC CHAT EXAMPLE")
    print("="*60)
    
    user_id = "student_alice"
    
    # Simple conversation
    messages = [
        "Hi! I'm new to programming. Can you help me?",
        "What's the difference between a variable and a function?",
        "Can you give me a simple example in Python?"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Turn {i} ---")
        print(f"Student: {message}")
        
        response = persona.chat(message, user_id=user_id)
        print(f"AI Tutor: {response}")


def memory_demonstration(persona: Persona):
    """
    Demonstrate memory functionality and persistence.
    
    Args:
        persona: The AI persona to chat with
    """
    print("\n" + "="*60)
    print("🧠 MEMORY DEMONSTRATION")
    print("="*60)
    
    user_id = "student_bob"
    
    # First session - learning about the student
    print("\n--- Session 1: Getting to know the student ---")
    session_1_messages = [
        "Hi, I'm Bob. I'm studying computer science at university.",
        "I'm particularly interested in machine learning and AI.",
        "I have some experience with Python but I'm new to frameworks like TensorFlow."
    ]
    
    for message in session_1_messages:
        print(f"\nBob: {message}")
        response = persona.chat(message, user_id=user_id)
        print(f"AI Tutor: {response}")
    
    # End session to update memory
    print("\n--- Ending Session 1 (memory will be updated) ---")
    result = persona.endsession(user_id)
    print(f"Session ended: {result}")
    
    # Show what was remembered
    memory_info = persona.get_memory(user_id)
    print(f"\n--- What the AI remembered about Bob ---")
    profile = memory_info.get_profile()
    print(f"Profile: {format_profile_display(profile)}")
    events = memory_info.get_events()
    print(f"Events: {len(events)} events recorded")
    if events:
        for i, event in enumerate(events[-3:], 1):  # Show last 3 events
            print(f"  {i}. {event}")
    
    # Second session - AI should remember Bob
    print(f"\n--- Session 2: AI remembers Bob (simulating next day) ---")
    memory_test_messages = [
        "Hi again! Do you remember me?",
        "I wanted to continue learning about machine learning. What should I focus on next?"
    ]
    
    for message in memory_test_messages:
        print(f"\nBob: {message}")
        response = persona.chat(message, user_id=user_id)
        print(f"AI Tutor: {response}")


def multi_user_example(persona: Persona):
    """
    Demonstrate multi-user conversations with memory isolation.
    
    Args:
        persona: The AI persona to chat with
    """
    print("\n" + "="*60)
    print("👥 MULTI-USER EXAMPLE")
    print("="*60)
    
    users = {
        "student_charlie": {
            "name": "Charlie",
            "intro": "Hi, I'm Charlie. I'm learning web development and need help with JavaScript.",
            "follow_up": "Can you explain what async/await is in JavaScript?"
        },
        "student_diana": {
            "name": "Diana",
            "intro": "Hello! I'm Diana, a data scientist. I want to learn about deep learning.",
            "follow_up": "What's the difference between CNN and RNN neural networks?"
        }
    }
    
    # Have conversations with different users
    for user_id, user_info in users.items():
        print(f"\n--- Conversation with {user_info['name']} ---")
        
        # Introduction
        print(f"\n{user_info['name']}: {user_info['intro']}")
        response1 = persona.chat(user_info['intro'], user_id=user_id)
        print(f"AI Tutor: {response1}")
        
        # Follow-up question
        print(f"\n{user_info['name']}: {user_info['follow_up']}")
        response2 = persona.chat(user_info['follow_up'], user_id=user_id)
        print(f"AI Tutor: {response2}")
        
        # End session
        persona.endsession(user_id)
    
    # Show memory isolation
    print(f"\n--- Memory Isolation Check ---")
    for user_id, user_info in users.items():
        memory = persona.get_memory(user_id)
        print(f"\n{user_info['name']}'s memory:")
        profile = memory.get_profile()
        print(f"  Profile: {format_profile_display(profile)}")
        events = memory.get_events()
        print(f"  Events: {len(events)} events")


def retrieval_demonstration(persona: Persona):
    """
    Demonstrate memory retrieval functionality with visual indicators.
    
    Args:
        persona: The AI persona to chat with
    """
    print("\n" + "="*60)
    print("🔍 MEMORY RETRIEVAL DEMONSTRATION")
    print("="*60)
    print("This example shows how PersonaLab retrieves relevant memories")
    print("when responding to user messages.")
    
    user_id = "student_frank"
    
    # Build up some memory first
    print("\n--- Building Memory (Session 1) ---")
    initial_messages = [
        "Hi, I'm Frank. I'm 25 years old and work as a data analyst.",
        "I want to learn Python for data science. I know some SQL and Excel.",
        "My goal is to automate my daily reports and do more advanced analytics.",
        "I'm particularly interested in pandas and matplotlib libraries."
    ]
    
    for i, message in enumerate(initial_messages, 1):
        print(f"\n💬 Frank: {message}")
        print("🔍 Retrieval: [Building initial memory...]")
        response = persona.chat(message, user_id=user_id)
        print(f"🤖 AI Tutor: {response}")
    
    # End session to save memory
    print("\n--- Ending Session 1 (saving to long-term memory) ---")
    persona.endsession(user_id)
    
    # Show what was stored
    memory = persona.get_memory(user_id)
    print(f"\n📊 Memory Stored:")
    print(f"   Memory: {memory}")
    profile = memory.get_profile()
    print(f"   Profile: {format_profile_display(profile)}")
    events = memory.get_events()
    print(f"   Events: {len(events)} events recorded")
    
    # New session with questions that should trigger retrieval
    print("\n" + "="*60)
    print("--- Session 2: Triggering Memory Retrieval ---")
    print("="*60)
    print("Now watch how PersonaLab retrieves relevant memories:")
    
    retrieval_test_messages = [
        "Hi! Do you remember my background?",
        "What Python libraries did I mention being interested in?",
        "Given my background in data analysis, what should I learn first?",
        "Can you recommend a pandas tutorial based on what you know about me?"
    ]
    
    for i, message in enumerate(retrieval_test_messages, 1):
        print(f"\n--- Retrieval Test {i} ---")
        print(f"💬 Frank: {message}")
        print("🔍 PersonaLab is now searching memory for relevant context...")
        print("   → Looking for: user background, previous interests, goals")
        
        response = persona.chat(message, user_id=user_id)
        
        print(f"✅ Memory retrieved and used in response!")
        print(f"🤖 AI Tutor: {response}")
        
        # Show a brief pause to emphasize the retrieval process
        import time
        time.sleep(0.5)


def session_management_example(persona: Persona):
    """
    Demonstrate session management and conversation history.
    
    Args:
        persona: The AI persona to chat with
    """
    print("\n" + "="*60)
    print("📊 SESSION MANAGEMENT EXAMPLE")
    print("="*60)
    
    user_id = "student_eve"
    
    # Multiple sessions over time
    sessions = [
        {
            "topic": "Variables and Data Types",
            "messages": [
                "I want to learn about Python variables.",
                "What are the main data types in Python?",
                "Can you show me how to use lists?"
            ]
        },
        {
            "topic": "Functions and Loops", 
            "messages": [
                "Now I want to learn about functions.",
                "How do I write a for loop in Python?",
                "Can you show me a function that uses a loop?"
            ]
        }
    ]
    
    for i, session in enumerate(sessions, 1):
        print(f"\n--- Session {i}: {session['topic']} ---")
        
        for message in session['messages']:
            print(f"\nEve: {message}")
            if i > 1:  # Show retrieval info for later sessions
                print("🔍 Checking memory for previous learning context...")
            response = persona.chat(message, user_id=user_id)
            print(f"AI Tutor: {response}")
        
        # End session
        print(f"\n--- Ending Session {i} ---")
        persona.endsession(user_id)
    
    # Show final memory state
    final_memory = persona.get_memory(user_id)
    print(f"\n--- Eve's Learning Journey Summary ---")
    events = final_memory.get_events()
    print(f"Total events recorded: {len(events)}")
    profile = final_memory.get_profile()
    print(f"Profile: {format_profile_display(profile)}")
    mind = final_memory.get_mind()
    if mind:
        print(f"AI insights about Eve: {mind}")


def cleanup_example(persona: Persona):
    """
    Demonstrate proper cleanup and resource management.
    
    Args:
        persona: The AI persona to clean up
    """
    print("\n" + "="*60)
    print("🧹 CLEANUP")
    print("="*60)
    
    try:
        # Close persona and release resources
        persona.close()
        print("✅ Persona resources cleaned up successfully")
    except Exception as e:
        print(f"⚠️ Warning during cleanup: {e}")


def main():
    """Main function demonstrating PersonaLab Persona chat functionality."""
    
    print("🤖 PersonaLab Persona Chat Example")
    print("=" * 50)
    print("This example demonstrates:")
    print("✅ Basic chat functionality")
    print("✅ Memory management and persistence")
    print("🔍 Memory retrieval visualization")
    print("✅ Multi-user conversations")
    print("✅ Session management")
    print("✅ Historical context retrieval")
    print("\n" + "="*50)
    
    # Create AI tutor persona
    persona = create_ai_tutor()
    if not persona:
        print("❌ Failed to create persona. Please check your configuration.")
        return 1
    
    try:
        # Run examples
        basic_chat_example(persona)
        memory_demonstration(persona) 
        retrieval_demonstration(persona)  # NEW: Dedicated retrieval demo
        multi_user_example(persona)
        session_management_example(persona)
        
        print("\n" + "="*60)
        print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n💡 Key Takeaways:")
        print("• PersonaLab automatically manages memory across sessions")
        print("• Each user has isolated memory spaces")
        print("• The AI learns about users over time")
        print("• Historical context enhances conversation quality")
        print("• Session management helps organize learning progress")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        return 1
    finally:
        # Always cleanup
        cleanup_example(persona)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 