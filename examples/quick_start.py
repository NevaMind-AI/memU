#!/usr/bin/env python3
"""
PersonaLab + OpenAI Quick Start Example

The simplest possible example showing how to use PersonaLab memory
with OpenAI ChatGPT API in just a few lines of code.

Usage:
    python quick_start.py
"""

import os
from openai import OpenAI
from personalab.utils import enhance_system_prompt_with_memory
from personalab.memory import MemoryClient


def main():
    """Quick start example - minimal code to get started."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key'")
        return
    
    print("🚀 PersonaLab + OpenAI Quick Start")
    print("=" * 40)
    
    # 1. Initialize PersonaLab memory
    memory_client = MemoryClient("quickstart.db")
    agent_id = "quickstart_user"
    
    # 2. Add some user information
    memory_client.update_profile(
        agent_id, 
        "User is a software developer interested in Python and AI"
    )
    memory_client.update_events(agent_id, [
        "Asked about machine learning libraries",
        "Discussed Python best practices"
    ])
    
    # 3. Get memory for the user
    memory = memory_client.get_memory_by_agent(agent_id)
    
    # 4. Create enhanced system prompt
    base_prompt = "You are a helpful coding assistant."
    enhanced_prompt = enhance_system_prompt_with_memory(
        base_system_prompt=base_prompt,
        memory=memory
    )
    
    print("📝 Enhanced System Prompt:")
    print("-" * 40)
    print(enhanced_prompt)
    print("-" * 40)
    
    # 5. Use with OpenAI
    client = OpenAI()
    user_message = "What Python libraries should I learn for machine learning?"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=200
    )
    
    print(f"\n💬 User: {user_message}")
    print(f"🤖 Assistant: {response.choices[0].message.content}")
    
    # 6. Update memory with multi-turn conversation
    # The update_memory_with_conversation method accepts List[Dict[str, str]] where:
    # - Each dict represents one conversation turn with 'role' and 'content' keys
    # - You can pass entire conversation histories or individual exchanges
    # - The method processes all turns together for better context understanding
    multi_turn_conversation = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response.choices[0].message.content},
        {"role": "user", "content": "I'm particularly interested in deep learning. Any specific recommendations?"},
        {"role": "assistant", "content": "For deep learning, I'd recommend starting with TensorFlow or PyTorch. TensorFlow has excellent documentation and Keras integration, while PyTorch is popular in research for its dynamic computation graphs."},
        {"role": "user", "content": "Thanks! I'll start with TensorFlow since I prefer good documentation."}
    ]
    
    updated_memory, result = memory_client.update_memory_with_conversation(
        agent_id, 
        multi_turn_conversation  # Can process entire conversation history at once
    )
    
    print(f"\n💾 Memory updated from multi-turn conversation: {result.update_result.profile_updated}")
    print("✅ Quick start completed!")


if __name__ == "__main__":
    main() 