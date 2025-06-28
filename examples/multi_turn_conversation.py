#!/usr/bin/env python3
"""
PersonaLab Multi-Turn Conversation Example

Demonstrates how to use PersonaLab memory with multi-turn conversations,
showing different conversation patterns and memory update strategies.

Usage:
    python multi_turn_conversation.py
"""

import os
from personalab.memory import MemoryClient


def example_1_sequential_conversations():
    """Example 1: Sequential conversation updates - updating after each exchange"""
    print("\n" + "="*60)
    print("📝 Example 1: Sequential Conversation Updates")
    print("="*60)
    
    memory_client = MemoryClient("multi_turn_example.db")
    agent_id = "user_sequential"
    
    # Conversation Turn 1
    conversation_turn_1 = [
        {"role": "user", "content": "Hi, I'm learning Python programming"},
        {"role": "assistant", "content": "Great! Python is an excellent language to learn. What specifically interests you about Python?"}
    ]
    
    memory, result = memory_client.update_memory_with_conversation(agent_id, conversation_turn_1)
    print(f"Turn 1 - Profile updated: {result.update_result.profile_updated}")
    
    # Conversation Turn 2  
    conversation_turn_2 = [
        {"role": "user", "content": "I want to build web applications"},
        {"role": "assistant", "content": "For web development in Python, I recommend learning Flask or Django. Flask is simpler to start with."}
    ]
    
    memory, result = memory_client.update_memory_with_conversation(agent_id, conversation_turn_2)
    print(f"Turn 2 - Profile updated: {result.update_result.profile_updated}")
    
    # Conversation Turn 3
    conversation_turn_3 = [
        {"role": "user", "content": "I also want to work with databases. What should I learn?"},
        {"role": "assistant", "content": "For databases with Python, SQLAlchemy is excellent for ORM, and you should learn SQL basics. PostgreSQL or MySQL are good choices."}
    ]
    
    memory, result = memory_client.update_memory_with_conversation(agent_id, conversation_turn_3)
    print(f"Turn 3 - Profile updated: {result.update_result.profile_updated}")
    
    print(f"\nFinal memory for {agent_id}:")
    print("-" * 40)
    print(memory.to_prompt())


def example_2_batch_conversation():
    """Example 2: Batch conversation update - updating entire conversation at once"""
    print("\n" + "="*60)
    print("📝 Example 2: Batch Conversation Update")
    print("="*60)
    
    memory_client = MemoryClient("multi_turn_example.db")
    agent_id = "user_batch"
    
    # Complete multi-turn conversation
    full_conversation = [
        {"role": "user", "content": "I'm a data scientist working with machine learning"},
        {"role": "assistant", "content": "Excellent! What kind of ML problems are you working on?"},
        {"role": "user", "content": "Mainly computer vision and NLP. I use TensorFlow and PyTorch"},
        {"role": "assistant", "content": "Those are powerful frameworks! Are you working on any specific projects?"},
        {"role": "user", "content": "Yes, I'm building an image classification system for medical diagnostics"},
        {"role": "assistant", "content": "That sounds very impactful! Medical AI is a fascinating field. Are you using pre-trained models?"},
        {"role": "user", "content": "I'm fine-tuning ResNet models and also experimenting with Vision Transformers"},
        {"role": "assistant", "content": "Great approach! Vision Transformers have shown excellent results in medical imaging. How's your dataset?"}
    ]
    
    memory, result = memory_client.update_memory_with_conversation(agent_id, full_conversation)
    print(f"Batch update - Profile updated: {result.update_result.profile_updated}")
    print(f"Conversation length: {len(full_conversation)} turns")
    
    print(f"\nFinal memory for {agent_id}:")
    print("-" * 40)
    print(memory.to_prompt())


def example_3_conversation_with_context():
    """Example 3: Adding context to ongoing conversations"""
    print("\n" + "="*60)
    print("📝 Example 3: Conversation with Historical Context")
    print("="*60)
    
    memory_client = MemoryClient("multi_turn_example.db")
    agent_id = "user_context"
    
    # Set initial user profile
    memory_client.update_profile(agent_id, "User is a software engineer with 5 years experience")
    memory_client.update_events(agent_id, [
        "Previously asked about React vs Vue",
        "Interested in full-stack development",
        "Works at a startup company"
    ])
    
    # New conversation builds on existing context
    new_conversation = [
        {"role": "user", "content": "I've decided to go with React. Now I need to choose a backend framework"},
        {"role": "assistant", "content": "Good choice on React! For backend, considering your full-stack goals, Node.js with Express would be great since you'd use JavaScript throughout."},
        {"role": "user", "content": "That makes sense. What about databases? Our startup is growing fast"},
        {"role": "assistant", "content": "For a growing startup, PostgreSQL is excellent for relational data, and Redis for caching. Consider MongoDB if you need flexible document storage."},
        {"role": "user", "content": "Perfect! I'll start with PostgreSQL and add Redis for caching later"}
    ]
    
    print("Before update:")
    print("-" * 40)
    print(memory_client.get_memory_by_agent(agent_id).to_prompt())
    
    memory, result = memory_client.update_memory_with_conversation(agent_id, new_conversation)
    print(f"\nContext-aware update - Profile updated: {result.update_result.profile_updated}")
    
    print(f"\nAfter update:")
    print("-" * 40)
    print(memory.to_prompt())


def example_4_different_conversation_styles():
    """Example 4: Different conversation styles and formats"""
    print("\n" + "="*60)
    print("📝 Example 4: Different Conversation Styles")
    print("="*60)
    
    memory_client = MemoryClient("multi_turn_example.db")
    agent_id = "user_styles"
    
    # Style 1: Q&A format
    qa_conversation = [
        {"role": "user", "content": "What's the difference between REST and GraphQL?"},
        {"role": "assistant", "content": "REST uses multiple endpoints for different resources, while GraphQL uses a single endpoint with flexible queries."},
        {"role": "user", "content": "Which one should I use for my project?"},
        {"role": "assistant", "content": "It depends on your needs. REST is simpler and more established. GraphQL is better for complex data requirements."}
    ]
    
    # Style 2: Problem-solving format  
    problem_solving_conversation = [
        {"role": "user", "content": "I'm getting a CORS error in my React app when calling my API"},
        {"role": "assistant", "content": "CORS errors happen when your frontend and backend are on different origins. You need to configure CORS on your server."},
        {"role": "user", "content": "How do I fix it in Express.js?"},
        {"role": "assistant", "content": "Install cors middleware: npm install cors, then app.use(cors()) in your Express app."},
        {"role": "user", "content": "That worked! Thanks for the help"}
    ]
    
    # Style 3: Learning/Tutorial format
    tutorial_conversation = [
        {"role": "assistant", "content": "Let's learn about async/await in JavaScript. Do you know what asynchronous programming is?"},
        {"role": "user", "content": "Not really, can you explain?"},
        {"role": "assistant", "content": "Async programming lets your code do other things while waiting for slow operations like API calls."},
        {"role": "user", "content": "Oh, so the code doesn't freeze while waiting?"},
        {"role": "assistant", "content": "Exactly! Now let's see how async/await makes this easier than callbacks or promises."}
    ]
    
    # Process each conversation style
    all_conversations = [
        ("Q&A Style", qa_conversation),
        ("Problem-Solving Style", problem_solving_conversation), 
        ("Tutorial Style", tutorial_conversation)
    ]
    
    for style_name, conversation in all_conversations:
        memory, result = memory_client.update_memory_with_conversation(agent_id, conversation)
        print(f"{style_name} - Profile updated: {result.update_result.profile_updated}")
    
    print(f"\nFinal consolidated memory:")
    print("-" * 40)
    print(memory.to_prompt())


def main():
    """Run all multi-turn conversation examples"""
    
    # Check if we have the required dependencies
    print("🚀 PersonaLab Multi-Turn Conversation Examples")
    
    try:
        example_1_sequential_conversations()
        example_2_batch_conversation()
        example_3_conversation_with_context()
        example_4_different_conversation_styles()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("💡 Key Takeaways:")
        print("   • update_memory_with_conversation accepts List[Dict[str, str]]")
        print("   • Each dict should have 'role' and 'content' keys")
        print("   • You can update after each turn or batch entire conversations")
        print("   • The system builds contextual understanding over time")
        print("   • Different conversation styles are all supported")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    main() 