"""
PersonaLab Profile Update Demo

This demo showcases the new profile update functionality where:
- Agent and user profiles can be updated based on conversations
- LLM intelligently extracts and integrates new information
- Profiles evolve over time while maintaining consistency
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab.main import Memory

def demo_agent_profile_update():
    """Demonstrate agent profile updating."""
    print("=== AGENT PROFILE UPDATE DEMO ===\n")
    
    # Create memory instance
    memory = Memory("learning_agent", enable_llm_judgment=True)
    
    # Set initial agent profile
    initial_profile = """
    I am an AI assistant focused on helping with programming and software development.
    I have experience with Python and basic web development.
    I enjoy helping users solve coding problems and learn new technologies.
    """
    
    memory.agent_memory.profile.set_profile(initial_profile.strip())
    
    print("Initial Agent Profile:")
    print(f"'{memory.agent_memory.profile.get_profile()}'")
    print()
    
    # Simulate conversations that should update the profile
    conversations = [
        """
        User: I'm working on a machine learning project using PyTorch. Can you help me with neural network architectures?
        Agent: Absolutely! I'd love to help you with PyTorch and neural networks. I have experience with CNNs, RNNs, and transformer architectures. What specific aspect are you working on?
        User: I'm trying to implement a custom attention mechanism.
        Agent: Great! I've worked with attention mechanisms before, including self-attention and cross-attention. Let me help you design the architecture.
        """,
        
        """
        User: Do you know anything about cloud deployment?
        Agent: Yes, I have experience with AWS, Docker containers, and Kubernetes for deploying ML models. I can help you set up CI/CD pipelines and monitoring systems.
        User: That's exactly what I need! I'm deploying a recommendation system.
        Agent: Perfect! I've worked on recommendation systems before, including collaborative filtering and deep learning approaches.
        """,
        
        """
        User: I'm interested in natural language processing.
        Agent: NLP is one of my favorite areas! I have extensive experience with transformers, BERT, GPT models, and various NLP tasks like sentiment analysis, named entity recognition, and text generation.
        User: Can you help me fine-tune a language model?
        Agent: Absolutely! I specialize in model fine-tuning, parameter-efficient methods like LoRA, and handling different datasets for NLP tasks.
        """
    ]
    
    # Update profile with each conversation
    for i, conversation in enumerate(conversations, 1):
        print(f"--- Conversation {i} ---")
        print(f"Content: {conversation[:100]}...")
        print()
        
        # Update agent profile
        updated_profile = memory.update_agent_profile_memory(conversation)
        
        print(f"Updated Agent Profile:")
        print(f"'{updated_profile}'")
        print()
        print("="*80)
        print()


def demo_user_profile_update():
    """Demonstrate user profile updating."""
    print("=== USER PROFILE UPDATE DEMO ===\n")
    
    # Create memory instance
    memory = Memory("adaptive_agent", enable_llm_judgment=True)
    
    # Start with minimal user information
    user_id = "data_scientist_alex"
    user_memory = memory.get_user_memory(user_id)
    user_memory.profile.set_profile("Data scientist interested in machine learning.")
    
    print("Initial User Profile:")
    print(f"'{user_memory.profile.get_profile()}'")
    print()
    
    # Simulate conversations that reveal more about the user
    user_conversations = [
        """
        User: Hi, I'm Alex. I'm a senior data scientist at TechCorp working on computer vision projects.
        Agent: Nice to meet you, Alex! Computer vision is fascinating. What kind of projects are you working on?
        User: I'm developing object detection models for autonomous vehicles. I have 8 years of experience in deep learning and specialize in CNN architectures.
        Agent: That's impressive! Autonomous vehicle CV is cutting-edge work.
        """,
        
        """
        User: I'm also pursuing a PhD in Computer Science at Stanford, focusing on efficient neural network architectures.
        Agent: A PhD at Stanford - that's excellent! Efficient architectures are crucial for practical deployment.
        User: Yes, my research focuses on model compression and knowledge distillation. I've published several papers on pruning techniques.
        Agent: That's valuable research, especially for edge deployment scenarios.
        """,
        
        """
        User: In my free time, I enjoy rock climbing and photography. I actually use computer vision techniques to analyze climbing routes!
        Agent: What an interesting combination! Using CV for route analysis is creative.
        User: I'm also fluent in Python, C++, and recently started learning Rust for performance-critical applications.
        Agent: Rust is a great choice for performance. Are you planning to use it for CV applications?
        """
    ]
    
    # Update user profile with each conversation
    for i, conversation in enumerate(user_conversations, 1):
        print(f"--- User Conversation {i} ---")
        print(f"Content: {conversation[:100]}...")
        print()
        
        # Update user profile
        updated_profile = memory.update_user_profile_memory(user_id, conversation)
        
        print(f"Updated User Profile:")
        print(f"'{updated_profile}'")
        print()
        print("="*80)
        print()


def demo_profile_consistency():
    """Demonstrate profile consistency and validation."""
    print("=== PROFILE CONSISTENCY DEMO ===\n")
    
    memory = Memory("consistent_agent", enable_llm_judgment=True)
    
    # Set initial profile
    initial_profile = "I am a web development specialist with 5 years of experience in React and Node.js."
    memory.agent_memory.profile.set_profile(initial_profile)
    
    print("Initial Profile:")
    print(f"'{initial_profile}'")
    print()
    
    # Test various types of conversations
    test_conversations = [
        ("Relevant update", """
         User: Can you help me with Python Flask development?
         Agent: Certainly! I have experience with Flask and can help you build web applications. I also work with FastAPI and Django.
         """),
        
        ("Irrelevant conversation", """
         User: What's the weather like today?
         Agent: I don't have access to current weather information, but I can help you find weather APIs to integrate into your applications.
         """),
        
        ("Contradictory information", """
         User: You mentioned you're new to programming, right?
         Agent: Actually, I have several years of experience in web development and various programming languages.
         """),
        
        ("Skill expansion", """
         User: Do you know about machine learning?
         Agent: Yes, I've been expanding my skills into ML recently. I'm learning PyTorch and working on computer vision projects alongside my web development work.
         """)
    ]
    
    for test_name, conversation in test_conversations:
        print(f"--- Test: {test_name} ---")
        print(f"Conversation: {conversation[:80]}...")
        
        profile_before = memory.agent_memory.profile.get_profile()
        updated_profile = memory.update_agent_profile_memory(conversation)
        
        if updated_profile != profile_before:
            print("✅ Profile updated")
            print(f"New profile: '{updated_profile[:150]}...'")
        else:
            print("⚪ Profile unchanged")
        
        print()


def demo_fallback_behavior():
    """Demonstrate fallback behavior when LLM is not available."""
    print("=== FALLBACK BEHAVIOR DEMO ===\n")
    
    # Create memory without LLM
    memory_no_llm = Memory("fallback_agent", enable_llm_judgment=False)
    
    # Set initial profile
    initial_profile = "Basic AI assistant."
    memory_no_llm.agent_memory.profile.set_profile(initial_profile)
    
    print("Testing fallback behavior (LLM disabled):")
    print(f"Initial profile: '{initial_profile}'")
    print()
    
    # Test conversation with clear profile information
    conversation = """
    User: Hi, I'm a software engineer. I work with Python and JavaScript.
    Agent: I'm an AI assistant. I specialize in helping with programming and development.
    """
    
    updated_profile = memory_no_llm.update_agent_profile_memory(conversation)
    
    print(f"Updated profile: '{updated_profile}'")
    print()
    
    if updated_profile != initial_profile:
        print("✅ Fallback method successfully extracted information")
    else:
        print("⚪ No changes detected by fallback method")


if __name__ == "__main__":
    print("PersonaLab Profile Update Functionality Demo")
    print("=" * 60)
    print()
    
    try:
        demo_agent_profile_update()
        print()
        
        demo_user_profile_update()
        print()
        
        demo_profile_consistency()
        print()
        
        demo_fallback_behavior()
        
        print("=" * 60)
        print("Profile Update Demo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc() 