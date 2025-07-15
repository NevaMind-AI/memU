#!/usr/bin/env python3
"""
Memory Agent Example

This example demonstrates how to use the new file-based MemoryAgent system:
- Creating character memories stored in .md files
- Reading and updating profiles and events
- Using agent tools for memory management
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memu.memory import Memory, MemoryAgent, MemoryFileManager
from memu.llm import OpenAIClient  # Optional: for LLM-powered memory analysis


def basic_memory_example():
    """Basic Memory class usage example"""
    print("=== Basic Memory Example ===")
    
    # Create a Memory instance for a character
    memory = Memory(character_name="Alice", memory_dir="character_memories")
    
    # Update profile
    profile_text = "Alice is a helpful AI assistant specializing in Python programming."
    memory.update_profile(profile_text)
    
    # Add some events
    events = [
        "Alice helped debug a complex algorithm",
        "Alice explained object-oriented programming concepts",
        "Alice reviewed code for optimization"
    ]
    memory.update_events(events)
    
    # Read back the data
    print(f"Character: {memory.character_name}")
    print(f"Profile: {memory.get_profile_content_string()}")
    print(f"Events: {memory.get_event_content()}")
    
    # Generate a prompt for LLM
    prompt = memory.to_prompt()
    print(f"Generated prompt:\n{prompt}")


def file_manager_example():
    """MemoryFileManager usage example"""
    print("\n=== File Manager Example ===")
    
    # Create file manager
    file_manager = MemoryFileManager("character_memories")
    
    # Write character data
    character = "Bob"
    profile = "Bob is an enthusiastic learner focused on machine learning."
    events_text = "Bob attended ML workshop\nBob implemented neural network"
    
    file_manager.write_profile(character, profile)
    file_manager.write_events(character, events_text)
    
    # Read back and display
    print(f"Bob's profile: {file_manager.read_profile(character)}")
    print(f"Bob's events: {file_manager.read_events(character)}")
    
    # List all characters
    characters = file_manager.list_characters()
    print(f"Available characters: {characters}")


def memory_agent_example():
    """MemoryAgent usage example"""
    print("\n=== Memory Agent Example ===")
    
    # Create MemoryAgent (without LLM for this example)
    agent = MemoryAgent(memory_dir="character_memories")
    
    # Use agent tools
    print("Available tools:")
    tools = agent.get_available_tools()
    for tool in tools:
        print(f"- {tool['function']['name']}: {tool['function']['description']}")
    
    # Read character profile using agent
    result = agent.read_character_profile("Alice")
    print(f"\nRead Alice profile: {result}")
    
    # Search for relevant events
    result = agent.search_relevant_events("Python", ["Alice", "Bob"], top_k=3)
    print(f"\nSearch results for 'Python': {result}")
    
    # Get character info
    result = agent.get_character_info("Alice")
    print(f"\nAlice info: {result}")


def llm_powered_example():
    """Example with LLM client (requires API key)"""
    print("\n=== LLM-Powered Memory Agent Example ===")
    
    try:
        # This requires OpenAI API key in environment
        # llm_client = OpenAIClient(api_key="your_api_key_here")
        # agent = MemoryAgent(llm_client=llm_client, memory_dir="character_memories")
        
        # Example conversation to analyze
        conversation = """
        User: Hi Alice, can you help me with Python decorators?
        Alice: Of course! Decorators are a powerful feature in Python that allow you to modify or extend functions.
        User: Can you show me an example?
        Alice: Sure! Here's a simple timing decorator...
        """
        
        # This would analyze the conversation and update memory
        # result = agent.update_character_memory("Alice", conversation, "2023-07-15")
        # print(f"Memory update result: {result}")
        
        print("LLM-powered features require an LLM client (OpenAI, Anthropic, etc.)")
        print("Set up your API key and uncomment the code above to use LLM features.")
        
    except Exception as e:
        print(f"LLM example skipped: {e}")


def cleanup_example():
    """Cleanup example"""
    print("\n=== Cleanup Example ===")
    
    file_manager = MemoryFileManager("character_memories")
    
    # Clear specific character memory
    results = file_manager.clear_character_memory("Alice")
    print(f"Cleared Alice's memory: {results}")
    
    # Clean up test directory
    import shutil
    from pathlib import Path
    test_dir = Path("character_memories")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("Cleaned up character_memories directory")


def main():
    """Run all examples"""
    print("MemoryAgent Examples\n" + "="*50)
    
    try:
        # Run examples
        basic_memory_example()
        file_manager_example()
        memory_agent_example()
        llm_powered_example()
        
        print("\n" + "="*50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error in examples: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        cleanup_example()


if __name__ == "__main__":
    main() 