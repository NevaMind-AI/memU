#!/usr/bin/env python3
"""
PersonaLab Personality Demo
==========================

This example demonstrates how to use the personality parameter to create 
AI assistants with different characters and behaviors.

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys (or use mock LLM for demo)
"""

import os
from personalab import Persona
from personalab.llm import CustomLLMClient


def create_mock_llm():
    """Create a mock LLM for demonstration purposes"""
    def mock_llm_function(messages, **kwargs):
        system_content = messages[0]['content'] if messages[0]['role'] == 'system' else ""
        user_msg = messages[-1]['content'].lower()
        
        # Show that personality is being used
        if "tutor" in system_content.lower():
            return "Let me help you learn! I love making complex topics easy to understand. " + \
                   f"Regarding your question about '{user_msg}', let's break it down step by step."
        elif "therapist" in system_content.lower():
            return "I hear you, and I want you to know that your feelings are valid. " + \
                   f"When you mention '{user_msg}', it sounds like something important to you. How does that make you feel?"
        elif "pirate" in system_content.lower():
            return f"Ahoy there, matey! Ye be askin' about '{user_msg}', eh? " + \
                   "Let me share me treasure of knowledge with ye, har har!"
        elif "chef" in system_content.lower():
            return f"Ah, magnificent! You're asking about '{user_msg}'. " + \
                   "In the kitchen of life, every ingredient matters! Let me share a delicious insight with you."
        else:
            return f"I understand you're asking about '{user_msg}'. How can I help you today?"
    
    return CustomLLMClient(llm_function=mock_llm_function)


def demo_different_personalities():
    """Demonstrate different AI personalities"""
    print("🎭 PersonaLab Personality Demo")
    print("=" * 50)
    
    # Define different personalities
    personalities = {
        "Friendly Tutor": {
            "personality": "You are a friendly and patient tutor who loves helping students learn. " +
                          "You explain concepts clearly, use encouraging language, and make learning fun.",
            "test_message": "I'm struggling with Python functions"
        },
        
        "Supportive Therapist": {
            "personality": "You are a compassionate and understanding therapist. " +
                          "You listen carefully, validate emotions, and provide gentle guidance.",
            "test_message": "I've been feeling stressed about work lately"
        },
        
        "Pirate Captain": {
            "personality": "You are a jolly pirate captain who speaks in pirate dialect. " +
                          "You're adventurous, use nautical terms, and say 'arr' and 'matey' often.",
            "test_message": "What's the best way to find treasure?"
        },
        
        "Master Chef": {
            "personality": "You are an enthusiastic master chef who is passionate about cooking. " +
                          "You use culinary metaphors and speak with flair about food and life.",
            "test_message": "How do I improve my cooking skills?"
        },
        
        "Default Assistant": {
            "personality": None,  # No personality - will use default
            "test_message": "What's the weather like today?"
        }
    }
    
    # Test each personality
    for name, config in personalities.items():
        print(f"\n🤖 Testing: {name}")
        print("-" * 30)
        
        # Create persona with or without personality
        if config["personality"]:
            print(f"Personality: {config['personality'][:60]}...")
            
            if os.getenv('OPENAI_API_KEY'):
                persona = Persona(
                    agent_id=f"demo_{name.lower().replace(' ', '_')}",
                    personality=config["personality"],
                    use_memory=False,
                    use_memo=False
                )
            else:
                mock_client = create_mock_llm()
                persona = Persona(
                    agent_id=f"demo_{name.lower().replace(' ', '_')}",
                    llm_client=mock_client,
                    personality=config["personality"],
                    use_memory=False,
                    use_memo=False
                )
        else:
            print("Personality: Default (helpful AI assistant)")
            
            if os.getenv('OPENAI_API_KEY'):
                persona = Persona(
                    agent_id="demo_default",
                    use_memory=False,
                    use_memo=False
                )
            else:
                mock_client = create_mock_llm()
                persona = Persona(
                    agent_id="demo_default",
                    llm_client=mock_client,
                    use_memory=False,
                    use_memo=False
                )
        
        # Test conversation
        test_msg = config["test_message"]
        print(f"\nUser: {test_msg}")
        
        try:
            response = persona.chat(test_msg, learn=False)
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
        
        persona.close()
        print()


def demo_personality_with_memory():
    """Demonstrate personality combined with memory functionality"""
    print("🧠 Personality + Memory Demo")
    print("=" * 50)
    
    # Create a coding mentor with personality
    coding_mentor_personality = """You are CodeMentor, an experienced software engineer and mentor. 
You are patient, encouraging, and passionate about teaching programming. 
You provide practical advice, share real-world insights, and always encourage best practices.
You speak with enthusiasm about coding and love helping developers grow."""
    
    if os.getenv('OPENAI_API_KEY'):
        persona = Persona(
            agent_id="coding_mentor",
            personality=coding_mentor_personality,
            use_memory=True,
            use_memo=True
        )
    else:
        mock_client = create_mock_llm()
        persona = Persona(
            agent_id="coding_mentor",
            llm_client=mock_client,
            personality=coding_mentor_personality,
            use_memory=True,
            use_memo=True
        )
    
    print("🎯 Personality: Experienced Coding Mentor")
    print("✅ Memory: Enabled")
    print("✅ Conversation History: Enabled")
    
    # Simulate a learning session
    conversations = [
        "Hi! I'm new to programming and want to learn Python.",
        "I've been practicing loops and functions. Can you give me a challenging project?",
        "What do you think about my progress so far?"
    ]
    
    for i, msg in enumerate(conversations, 1):
        print(f"\n[Turn {i}]")
        print(f"Student: {msg}")
        
        try:
            response = persona.chat(msg)
            print(f"CodeMentor: {response}")
        except Exception as e:
            print(f"CodeMentor: [Error: {e}]")
    
    # Show what was remembered
    print(f"\n🧠 Memory Summary:")
    memory = persona.get_memory()
    for key, values in memory.items():
        if values:
            print(f"  {key}: {len(values)} items")
    
    persona.close()


def demo_interactive_personality():
    """Interactive demo where user can test different personalities"""
    print("\n🎮 Interactive Personality Test")
    print("=" * 50)
    print("Choose a personality to chat with:")
    print("1. Friendly Teacher")
    print("2. Wise Philosopher") 
    print("3. Enthusiastic Coach")
    print("4. Curious Scientist")
    print("0. Skip interactive demo")
    
    choice = input("\nEnter your choice (0-4): ").strip()
    
    if choice == "0":
        print("Skipping interactive demo.")
        return
    
    personalities = {
        "1": "You are a friendly and patient teacher who loves helping students discover new things. You use simple explanations and encouraging words.",
        "2": "You are a wise philosopher who thinks deeply about life's big questions. You speak thoughtfully and often reference ancient wisdom.",
        "3": "You are an enthusiastic coach who motivates and inspires people to reach their full potential. You're energetic and always positive.",
        "4": "You are a curious scientist who loves exploring how things work. You ask thoughtful questions and explain things with scientific wonder."
    }
    
    if choice in personalities:
        selected_personality = personalities[choice]
        personality_names = {
            "1": "Friendly Teacher",
            "2": "Wise Philosopher", 
            "3": "Enthusiastic Coach",
            "4": "Curious Scientist"
        }
        
        print(f"\n✅ You selected: {personality_names[choice]}")
        print(f"Personality: {selected_personality[:60]}...")
        
        if os.getenv('OPENAI_API_KEY'):
            persona = Persona(
                agent_id="interactive_demo",
                personality=selected_personality,
                use_memory=False,
                use_memo=False
            )
        else:
            mock_client = create_mock_llm()
            persona = Persona(
                agent_id="interactive_demo",
                llm_client=mock_client,
                personality=selected_personality,
                use_memory=False,
                use_memo=False
            )
        
        print("\nType 'quit' to exit the chat")
        print("-" * 30)
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input:
                try:
                    response = persona.chat(user_input, learn=False)
                    print(f"AI: {response}")
                except Exception as e:
                    print(f"AI: [Error: {e}]")
        
        persona.close()
        print("✅ Chat ended!")
    else:
        print("Invalid choice. Skipping interactive demo.")


def main():
    """Main function"""
    print("🎭 PersonaLab Personality Parameter Demo")
    print("=" * 50)
    print("This demo shows how to use the personality parameter to create")
    print("AI assistants with different characters and behaviors.\n")
    
    try:
        # Run demos
        demo_different_personalities()
        demo_personality_with_memory()
        demo_interactive_personality()
        
        print("\n✅ Personality Demo Complete!")
        print("=" * 50)
        print("\n💡 Key Features Demonstrated:")
        print("  • Creating AI assistants with distinct personalities")
        print("  • Combining personality with memory functionality")
        print("  • How personality affects conversation style")
        print("  • Interactive testing of different characters")
        
        print("\n🎯 Usage Tips:")
        print("  • Be specific about personality traits and communication style")
        print("  • Consider your use case (tutor, assistant, coach, etc.)")
        print("  • Personality works with all LLM providers")
        print("  • Combine with memory for consistent character development")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 