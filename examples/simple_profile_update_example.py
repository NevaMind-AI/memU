"""
Simple Profile Update Example

Shows how to use the new update_profile_memory functions for both agent and user profiles.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab.main import Memory

def main():
    """Simple example of profile updating."""
    
    # Create memory instance
    memory = Memory("learning_ai", enable_llm_judgment=True)
    
    print("=== Profile Update Example ===\n")
    
    # 1. Agent Profile Update
    print("1. AGENT PROFILE UPDATE")
    print("-" * 30)
    
    # Set initial agent profile
    memory.agent_memory.profile.set_profile("I am a helpful AI assistant.")
    
    print(f"Initial agent profile: '{memory.agent_memory.profile.get_profile()}'")
    
    # Simulate a conversation where agent demonstrates new capabilities
    conversation = """
    User: Can you help me with data analysis in Python?
    Agent: Absolutely! I have experience with pandas, numpy, matplotlib, and scikit-learn. 
           I can help you with data cleaning, visualization, and machine learning models.
    User: That's great! What about deep learning?
    Agent: Yes, I'm familiar with PyTorch and TensorFlow. I can assist with neural networks, 
           computer vision, and natural language processing tasks.
    """
    
    print(f"\nConversation: {conversation[:100]}...")
    
    # Update agent profile
    updated_agent_profile = memory.update_agent_profile_memory(conversation)
    
    print(f"\nUpdated agent profile: '{updated_agent_profile}'")
    print()
    
    # 2. User Profile Update
    print("2. USER PROFILE UPDATE")
    print("-" * 30)
    
    user_id = "scientist_bob"
    
    # Set initial user profile
    user_memory = memory.get_user_memory(user_id)
    user_memory.profile.set_profile("Researcher working in life sciences.")
    
    print(f"Initial user profile: '{user_memory.profile.get_profile()}'")
    
    # Simulate conversation revealing more about user
    user_conversation = """
    User: Hi, I'm Bob. I work at BioCorp as a computational biologist.
    Agent: Nice to meet you, Bob! Computational biology is fascinating.
    User: I specialize in genomics and use Python for sequence analysis. 
          I have a PhD in Bioinformatics from MIT and 10 years of experience.
    Agent: That's impressive! Genomics research is cutting-edge.
    User: I'm currently working on protein folding prediction using deep learning.
    """
    
    print(f"\nUser conversation: {user_conversation[:100]}...")
    
    # Update user profile
    updated_user_profile = memory.update_user_profile_memory(user_id, user_conversation)
    
    print(f"\nUpdated user profile: '{updated_user_profile}'")
    print()
    
    # 3. Show memory info
    print("3. MEMORY INFO")
    print("-" * 30)
    
    info = memory.get_memory_info()
    print(f"Agent ID: {info['agent_id']}")
    print(f"Agent profile length: {info['agent_profile_length']} characters")
    print(f"Number of users: {info['user_count']}")
    print(f"User profile length: {info['users'][user_id]['profile_length']} characters")
    print()
    
    # 4. Multiple updates example
    print("4. MULTIPLE UPDATES")
    print("-" * 30)
    
    print("Applying multiple conversations...")
    
    conversations = [
        "User: Do you know about machine learning? Agent: Yes, I work with various ML algorithms.",
        "User: What about cloud computing? Agent: I have experience with AWS and containerization.",
        "User: Any database knowledge? Agent: Yes, I work with SQL, MongoDB, and Redis."
    ]
    
    for i, conv in enumerate(conversations, 1):
        print(f"  Conversation {i}: {conv[:50]}...")
        memory.update_agent_profile_memory(conv)
    
    final_profile = memory.agent_memory.profile.get_profile()
    print(f"\nFinal agent profile after multiple updates:")
    print(f"'{final_profile}'")
    

if __name__ == "__main__":
    main() 