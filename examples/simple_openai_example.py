#!/usr/bin/env python3
"""
Simple PersonaLab + OpenAI Integration Example

A concise example showing how to use enhance_system_prompt_with_memory
with the modern OpenAI API (v1.x).
"""

import os
from openai import OpenAI
from personalab.utils import enhance_system_prompt_with_memory
from personalab.memory import MemoryClient


def main():
    """Main example demonstrating memory-enhanced OpenAI chat."""
    
    # 1. Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # 2. Setup PersonaLab memory
    memory_client = MemoryClient("example.db")
    agent_id = "user_001"
    
    # 3. Create and populate memory with sample data
    memory = memory_client.get_or_create_memory(agent_id)
    
    # Add user profile
    memory.update_profile(
        "User is a Python developer interested in AI and machine learning. "
        "Prefers practical examples and clean code. Works remotely."
    )
    
    # Add recent events  
    memory.update_events([
        "Asked about FastAPI performance optimization",
        "Discussed async/await patterns in Python",
        "Explored vector database integration"
    ])
    
    # Add behavioral insights
    memory.update_tom([
        "Prefers concise, actionable responses",
        "Learns best through working examples"
    ])
    
    # Save memory
    memory_client.repository.save_memory(memory)
    
    # 4. Create base system prompt
    base_prompt = """You are an expert Python developer and AI assistant.
Provide helpful, practical advice with code examples when appropriate."""
    
    # 5. Enhance prompt with memory context
    enhanced_prompt = enhance_system_prompt_with_memory(
        base_system_prompt=base_prompt,
        memory=memory,  # Pass Memory object directly
        include_profile=True,
        include_events=True, 
        include_insights=True,
        max_events=3,
        max_insights=2
    )
    
    print("🔧 Enhanced System Prompt:")
    print("=" * 50)
    print(enhanced_prompt)
    print("\n" + "=" * 50 + "\n")
    
    # 6. Use with OpenAI Chat
    user_message = "How can I make my Python API faster?"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    assistant_reply = response.choices[0].message.content
    
    print(f"💬 User: {user_message}")
    print(f"🤖 Assistant: {assistant_reply}")
    
    # 7. Alternative: Using agent_id string
    print("\n" + "=" * 50)
    print("📝 Alternative Usage (with agent_id string):")
    
    enhanced_prompt_alt = enhance_system_prompt_with_memory(
        base_system_prompt="You are a helpful coding assistant.",
        memory=agent_id,  # Pass agent_id as string
        memory_client=memory_client,  # Required when using agent_id
        max_events=2
    )
    
    print(enhanced_prompt_alt[:200] + "..." if len(enhanced_prompt_alt) > 200 else enhanced_prompt_alt)


def quick_demo():
    """Quick demonstration of the key features."""
    
    print("🚀 PersonaLab Memory Enhancement Demo")
    print("=" * 40)
    
    # Setup
    memory_client = MemoryClient("quick_demo.db") 
    memory = memory_client.get_or_create_memory("demo_user")
    
    # Add minimal memory data
    memory.update_profile("Software engineer learning LLM applications")
    memory.update_events(["Discussed API design patterns"])
    memory.update_tom(["Prefers practical examples"])
    
    # Enhance prompt
    base = "You are a helpful AI assistant."
    enhanced = enhance_system_prompt_with_memory(
        base_system_prompt=base,
        memory=memory
    )
    
    print("📄 Base prompt:", base)
    print("\n🔧 Enhanced prompt:")
    print(enhanced)


if __name__ == "__main__":
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set!")
        print("Set it with: export OPENAI_API_KEY='your-key'")
        print("\nRunning demo without OpenAI API call...\n")
        quick_demo()
    else:
        main()
        
    print("\n✅ Example completed!") 