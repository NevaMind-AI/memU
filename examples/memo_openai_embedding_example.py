#!/usr/bin/env python3
"""
PersonaLab Memo OpenAI Embedding Example

Demonstrates using OpenAI's text-embedding-ada-002 model for high-quality
conversation vectorization and semantic search.

Prerequisites:
1. Install OpenAI library: pip install openai
2. Set OpenAI API key as environment variable: export OPENAI_API_KEY="your-key"
   OR create a .env file with: OPENAI_API_KEY=your-key
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager


def check_openai_setup():
    """Check if OpenAI is properly configured."""
    try:
        import openai
        print("✅ OpenAI library is installed")
    except ImportError:
        print("❌ OpenAI library not found. Please install: pip install openai")
        return False
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Please set it with: export OPENAI_API_KEY='your-api-key'")
        print("   Or create a .env file with: OPENAI_API_KEY=your-api-key")
        return False
    
    print(f"✅ OpenAI API key found (ends with: ...{api_key[-4:]})")
    return True


def main():
    print("=== PersonaLab Memo OpenAI Embedding Example ===\n")
    
    # Check OpenAI setup
    if not check_openai_setup():
        print("\n❌ OpenAI setup incomplete. Please configure API key and try again.")
        return
    
    print("\n🚀 Initializing ConversationManager with OpenAI embeddings...")
    
    # Initialize conversation manager with OpenAI embeddings
    conversation_manager = ConversationManager(
        db_path="memo_openai_example.db",
        enable_embeddings=True,
        embedding_provider="openai"  # Use OpenAI embeddings (default model: text-embedding-ada-002)
    )
    
    agent_id = "openai_demo_agent"
    
    print("✅ ConversationManager initialized with OpenAI embeddings\n")
    
    # Test conversations with diverse topics for better embedding demonstration
    test_conversations = [
        {
            "user_id": "user_1",
            "topic": "Machine Learning",
            "messages": [
                {"role": "user", "content": "I'm working on a machine learning project using PyTorch. I'm trying to build a neural network for image classification."},
                {"role": "assistant", "content": "That sounds like an exciting project! Image classification with PyTorch is a great way to learn deep learning. What type of images are you classifying?"},
                {"role": "user", "content": "I'm working with medical X-ray images to detect pneumonia. I'm using a CNN with ResNet architecture."},
                {"role": "assistant", "content": "Medical image analysis is very impactful work! ResNet is an excellent choice for X-ray classification. Have you considered data augmentation techniques?"}
            ]
        },
        {
            "user_id": "user_2", 
            "topic": "Cooking",
            "messages": [
                {"role": "user", "content": "I love cooking Italian food, especially making fresh pasta from scratch. Do you have any tips for perfect pasta dough?"},
                {"role": "assistant", "content": "Fresh pasta is wonderful! The key is getting the right flour-to-egg ratio. I recommend using 100g of 00 flour per large egg."},
                {"role": "user", "content": "That's helpful! I've been struggling with the texture. Should I knead it by hand or use a machine?"},
                {"role": "assistant", "content": "Hand kneading gives you better feel for the dough. Knead for about 10 minutes until it's smooth and elastic."}
            ]
        },
        {
            "user_id": "user_3",
            "topic": "Travel",
            "messages": [
                {"role": "user", "content": "I'm planning a backpacking trip across Southeast Asia. I want to visit Thailand, Vietnam, and Cambodia over 3 weeks."},
                {"role": "assistant", "content": "What an amazing adventure! Three weeks is a good amount of time for those countries. Have you thought about your route and transportation?"},
                {"role": "user", "content": "I'm thinking of starting in Bangkok, then going to Ho Chi Minh City, and ending in Siem Reap to see Angkor Wat."},
                {"role": "assistant", "content": "That's a classic route! Make sure to try street food in each city - pad thai in Bangkok, pho in Ho Chi Minh, and fish amok in Cambodia."}
            ]
        },
        {
            "user_id": "user_4",
            "topic": "Programming",
            "messages": [
                {"role": "user", "content": "I'm learning Python programming and want to build web applications. Should I start with Django or Flask?"},
                {"role": "assistant", "content": "Both are excellent choices! Flask is lighter and easier to start with, while Django has more built-in features. What kind of applications do you want to build?"},
                {"role": "user", "content": "I want to create a personal blog with user authentication and a content management system."},
                {"role": "assistant", "content": "For that use case, Django might be better since it has built-in admin interface and user authentication. It'll save you development time."}
            ]
        }
    ]
    
    print("1. Recording conversations with diverse topics...")
    recorded_conversations = []
    
    for i, conv_data in enumerate(test_conversations, 1):
        print(f"   Recording conversation {i}: {conv_data['topic']}")
        
        recorded_conv = conversation_manager.record_conversation(
            agent_id=agent_id,
            messages=conv_data["messages"],
            user_id=conv_data["user_id"]
        )
        
        recorded_conversations.append(recorded_conv)
        print(f"   ✅ Recorded: {recorded_conv.conversation_id[:8]}... - {conv_data['topic']}")
    
    print(f"\n✅ Recorded {len(recorded_conversations)} conversations\n")
    
    # Demonstrate high-quality semantic search with OpenAI embeddings
    print("2. Testing semantic search with OpenAI embeddings...")
    
    search_queries = [
        {
            "query": "deep learning neural networks artificial intelligence",
            "description": "AI/ML related search"
        },
        {
            "query": "food recipes cooking techniques kitchen",
            "description": "Culinary search"
        },
        {
            "query": "vacation travel adventure exploration",
            "description": "Travel search"
        },
        {
            "query": "software development web frameworks backend",
            "description": "Programming search"
        },
        {
            "query": "medical healthcare diagnosis treatment",
            "description": "Medical search"
        }
    ]
    
    for search in search_queries:
        print(f"\n🔍 {search['description']}: '{search['query']}'")
        
        results = conversation_manager.search_similar_conversations(
            agent_id=agent_id,
            query=search["query"],
            limit=3,
            similarity_threshold=0.5
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"   {i}. Score: {result['similarity_score']:.3f}")
                print(f"      Content: {result['matched_content'][:80]}...")
                print(f"      Summary: {result['summary'][:60]}...")
                print()
        else:
            print("   No matches found above threshold")
    
    # Get embedding statistics
    print("3. Embedding Information:")
    stats = conversation_manager.get_conversation_stats(agent_id)
    print(f"   Model: {stats.get('embedding_model', 'Unknown')}")
    print(f"   Total conversations: {stats.get('total_conversations', 0)}")
    print(f"   Embedding enabled: {stats.get('embedding_enabled', False)}")
    
    # Demonstrate user-specific search
    print(f"\n4. User-specific conversation retrieval:")
    for user_id in ["user_1", "user_2", "user_3", "user_4"]:
        user_convs = conversation_manager.get_conversation_history(
            agent_id, 
            user_id=user_id,
            limit=5
        )
        
        if user_convs:
            conv = user_convs[0]
            print(f"   {user_id}: {conv['summary'][:50]}...")
    
    # Quality comparison example
    print(f"\n5. Embedding Quality Demonstration:")
    print("   OpenAI embeddings provide superior semantic understanding:")
    print("   - Better context understanding")
    print("   - More accurate similarity scoring") 
    print("   - Improved cross-topic relationships")
    print("   - Higher dimensional representations (1536D)")
    
    # Test edge case: very similar content
    print(f"\n6. Testing similar content discrimination...")
    
    similar_conversations = [
        [
            {"role": "user", "content": "I'm learning machine learning with Python and scikit-learn"},
            {"role": "assistant", "content": "That's great! Scikit-learn is perfect for beginners in ML."}
        ],
        [
            {"role": "user", "content": "I'm studying artificial intelligence using Python and TensorFlow"},
            {"role": "assistant", "content": "Excellent choice! TensorFlow is powerful for AI development."}
        ]
    ]
    
    for i, messages in enumerate(similar_conversations, 1):
        conv = conversation_manager.record_conversation(
            agent_id=agent_id,
            messages=messages,
            user_id=f"test_user_{i}"
        )
        print(f"   Recorded similar conversation {i}: {conv.conversation_id[:8]}...")
    
    # Search to see how well it distinguishes
    ml_results = conversation_manager.search_similar_conversations(
        agent_id=agent_id,
        query="machine learning scikit-learn",
        limit=5,
        similarity_threshold=0.3
    )
    
    print(f"\n   Search results for 'machine learning scikit-learn':")
    for i, result in enumerate(ml_results[:3], 1):
        print(f"   {i}. Score: {result['similarity_score']:.3f}")
        print(f"      Content: {result['matched_content'][:60]}...")
    
    print(f"\n=== OpenAI Embedding Example Completed Successfully! ===")
    print("\nOpenAI Embedding Benefits:")
    print("✅ High-quality semantic understanding")
    print("✅ 1536-dimensional vectors for rich representation")
    print("✅ Trained on diverse text for robust performance")
    print("✅ Excellent for production applications")
    print("✅ Strong performance across different domains")
    
    print(f"\nNote: This example used OpenAI's text-embedding-ada-002 model")
    print(f"Database saved to: memo_openai_example.db")


if __name__ == "__main__":
    main() 