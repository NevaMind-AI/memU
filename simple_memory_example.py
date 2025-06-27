#!/usr/bin/env python3
"""
Simple Memory Update Example

Shows the basic usage of the memory update pipeline.
"""

from personalab.memory import Memory, MemoryUpdatePipeline
from personalab.llm import create_llm_client
from personalab.config import config

def simple_example():
    """Simple memory update example"""
    
    # 1. Create memory
    memory = Memory("agent_001")
    memory.update_profile("User is a developer")
    
    # 2. Create pipeline with LLM
    # Note: You need to set OPENAI_API_KEY in .env file
    try:
        if config.validate_llm_config("openai"):
            llm_client = create_llm_client("openai", **config.get_llm_config("openai"))
            pipeline = MemoryUpdatePipeline(llm_client)
        else:
            raise Exception("No API key configured")
    except:
        # Fallback: create pipeline without LLM (will raise exceptions on use)
        pipeline = MemoryUpdatePipeline()
    
    # 3. Define conversation
    conversation = [
        {"role": "user", "content": "I love programming in Python"},
        {"role": "assistant", "content": "Python is great for many applications!"}
    ]
    
    # 4. Update memory
    try:
        new_memory, result = pipeline.update_with_pipeline(memory, conversation)
        
        print("Memory updated successfully!")
        print(f"New profile: {new_memory.get_profile_content()}")
        print(f"Events: {new_memory.get_event_content()}")
        print(f"ToM insights: {result.tom_result.insights}")
        
    except Exception as e:
        print(f"Update failed: {e}")

if __name__ == "__main__":
    simple_example() 