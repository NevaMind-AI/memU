#!/usr/bin/env python3
"""
PersonaLab Conversation Recording and Vector Search Example

Demonstrates the new conversation recording and vectorization features:
- Automatic conversation recording to database
- Vector embeddings generation for semantic search
- Conversation history retrieval and similarity search
- Multiple embedding provider support

Usage:
    python conversation_with_vector_search.py
"""

import os
import time
from personalab.memory import MemoryClient


def example_1_basic_conversation_recording():
    """Example 1: Basic conversation recording and retrieval"""
    print("\n" + "="*60)
    print("📝 Example 1: Basic Conversation Recording")
    print("="*60)
    
    # Initialize memory client with embedding support
    memory_client = MemoryClient(
        "conversation_example.db", 
        enable_embeddings=True,
        embedding_provider="simple"  # Use simple provider for demo
    )
    agent_id = "demo_user_1"
    
    # Record first conversation
    conversation_1 = [
        {"role": "user", "content": "I'm learning Python programming"},
        {"role": "assistant", "content": "Great! Python is excellent for beginners. What specific areas interest you?"},
        {"role": "user", "content": "I want to build web applications"},
        {"role": "assistant", "content": "For web development, I recommend Flask or Django. Flask is simpler to start with."}
    ]
    
    print("💬 Recording conversation 1...")
    memory, result = memory_client.update_memory_with_conversation(
        agent_id, 
        conversation_1,
        session_id="session_1"
    )
    print(f"✅ Conversation recorded. Profile updated: {result.update_result.profile_updated}")
    
    # Record second conversation
    conversation_2 = [
        {"role": "user", "content": "How do I connect Python to a database?"},
        {"role": "assistant", "content": "You can use SQLAlchemy for ORM or sqlite3 for direct database access."},
        {"role": "user", "content": "Which database should I use for my web app?"},
        {"role": "assistant", "content": "PostgreSQL is great for production, SQLite for development and small projects."}
    ]
    
    print("\n💬 Recording conversation 2...")
    memory, result = memory_client.update_memory_with_conversation(
        agent_id, 
        conversation_2,
        session_id="session_2"
    )
    print(f"✅ Conversation recorded. Profile updated: {result.update_result.profile_updated}")
    
    # Get conversation history
    print("\n📜 Conversation History:")
    print("-" * 40)
    history = memory_client.get_conversation_history(agent_id, limit=5)
    for i, conv in enumerate(history, 1):
        print(f"{i}. {conv['created_at'][:19]} - {conv['summary']}")
        print(f"   Session: {conv['session_id']}, Turns: {conv['turn_count']}")
    
    print(f"\n📊 Updated Memory Profile:")
    print("-" * 40)
    print(memory.to_prompt())


def example_2_semantic_conversation_search():
    """Example 2: Semantic search through conversation history"""
    print("\n" + "="*60)
    print("🔍 Example 2: Semantic Conversation Search")
    print("="*60)
    
    memory_client = MemoryClient(
        "conversation_example.db", 
        enable_embeddings=True,
        embedding_provider="simple"
    )
    agent_id = "demo_user_2"
    
    # Record multiple conversations on different topics
    conversations = [
        {
            "session": "ml_session",
            "messages": [
                {"role": "user", "content": "I want to learn machine learning"},
                {"role": "assistant", "content": "Machine learning is fascinating! Start with scikit-learn for basics."},
                {"role": "user", "content": "What about deep learning?"},
                {"role": "assistant", "content": "For deep learning, TensorFlow and PyTorch are the main frameworks."}
            ]
        },
        {
            "session": "web_session", 
            "messages": [
                {"role": "user", "content": "How do I build a REST API?"},
                {"role": "assistant", "content": "You can use Flask-RESTful or FastAPI for building REST APIs."},
                {"role": "user", "content": "What about authentication?"},
                {"role": "assistant", "content": "JWT tokens are commonly used for API authentication."}
            ]
        },
        {
            "session": "data_session",
            "messages": [
                {"role": "user", "content": "How to analyze data with Python?"},
                {"role": "assistant", "content": "Pandas is excellent for data analysis, matplotlib for visualization."},
                {"role": "user", "content": "What about big data?"},
                {"role": "assistant", "content": "For big data, consider Apache Spark with PySpark."}
            ]
        }
    ]
    
    # Record all conversations
    print("💬 Recording multiple conversations...")
    for i, conv_data in enumerate(conversations, 1):
        memory, result = memory_client.update_memory_with_conversation(
            agent_id,
            conv_data["messages"],
            session_id=conv_data["session"]
        )
        print(f"✅ Conversation {i} recorded (Session: {conv_data['session']})")
    
    # Perform semantic searches
    search_queries = [
        "artificial intelligence and neural networks",
        "building web services and APIs", 
        "data science and analytics",
        "database connections and storage"
    ]
    
    print(f"\n🔍 Semantic Search Results:")
    print("-" * 50)
    
    for query in search_queries:
        print(f"\n🔍 Query: '{query}'")
        results = memory_client.search_similar_conversations(
            agent_id, 
            query, 
            limit=3,
            similarity_threshold=0.1  # Lower threshold for demo
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result['similarity_score']:.3f}")
                print(f"     Session: {result['session_id']}")
                print(f"     Summary: {result['summary']}")
                print(f"     Content: {result['matched_content'][:100]}...")
        else:
            print("  No similar conversations found.")


def example_3_conversation_detail_and_retrieval():
    """Example 3: Detailed conversation retrieval and analysis"""
    print("\n" + "="*60)
    print("📋 Example 3: Conversation Detail and Retrieval")
    print("="*60)
    
    memory_client = MemoryClient("conversation_example.db")
    agent_id = "demo_user_3"
    
    # Record a detailed conversation
    detailed_conversation = [
        {"role": "user", "content": "I'm building a machine learning project for image classification"},
        {"role": "assistant", "content": "That's exciting! What type of images are you working with?"},
        {"role": "user", "content": "Medical X-ray images to detect pneumonia"},
        {"role": "assistant", "content": "Medical AI is very impactful. Are you using CNN architectures like ResNet or VGG?"},
        {"role": "user", "content": "I'm trying ResNet50 with transfer learning"},
        {"role": "assistant", "content": "Excellent choice! Pre-trained ResNet50 works well for medical imaging. Are you fine-tuning all layers?"},
        {"role": "user", "content": "Just the last few layers. My accuracy is around 85%"},
        {"role": "assistant", "content": "85% is good! You might improve with data augmentation and ensemble methods."}
    ]
    
    print("💬 Recording detailed conversation...")
    memory, result = memory_client.update_memory_with_conversation(
        agent_id, 
        detailed_conversation,
        session_id="ml_project_discussion"
    )
    
    conversation_id = result.pipeline_metadata.get('conversation_id') if hasattr(result, 'pipeline_metadata') else None
    
    # Get conversation history and show details
    print("\n📜 Recent Conversations:")
    print("-" * 40)
    recent_conversations = memory_client.get_conversation_history(agent_id, limit=3)
    
    if recent_conversations:
        latest_conv = recent_conversations[0]
        print(f"Latest Conversation ID: {latest_conv['conversation_id']}")
        print(f"Created: {latest_conv['created_at']}")
        print(f"Turns: {latest_conv['turn_count']}")
        print(f"Summary: {latest_conv['summary']}")
        
        # Get detailed conversation
        print(f"\n💭 Detailed Conversation:")
        print("-" * 40)
        detailed = memory_client.get_conversation_detail(latest_conv['conversation_id'])
        if detailed:
            for i, message in enumerate(detailed['messages'], 1):
                role = message['role'].upper()
                content = message['content']
                print(f"{i}. {role}: {content}")
    
    # Show updated memory
    print(f"\n🧠 Updated Memory Profile:")
    print("-" * 40)
    print(memory.to_prompt())


def example_4_embedding_providers():
    """Example 4: Different embedding providers comparison"""
    print("\n" + "="*60)
    print("🔬 Example 4: Embedding Providers Comparison")
    print("="*60)
    
    providers = [

        ("sentence-transformers", "Sentence Transformers (if available)"),
        ("openai", "OpenAI embeddings (if API key available)")
    ]
    
    for provider_type, description in providers:
        try:
            print(f"\n🔧 Testing {description}...")
            
            memory_client = MemoryClient(
                f"test_{provider_type}.db",
                enable_embeddings=True,
                embedding_provider=provider_type
            )
            
            if memory_client.embedding_manager:
                model_name = memory_client.embedding_manager.model_name
                dimension = memory_client.embedding_manager.embedding_dimension
                print(f"✅ Provider: {provider_type}")
                print(f"   Model: {model_name}")
                print(f"   Dimension: {dimension}")
                
                # Test embedding generation
                test_text = "This is a test conversation about machine learning"
                embedding = memory_client.embedding_manager.provider.generate_embedding(test_text)
                print(f"   Sample embedding length: {len(embedding)}")
                print(f"   First 5 values: {embedding[:5]}")
            else:
                print(f"❌ Failed to initialize {provider_type} provider")
                
        except Exception as e:
            print(f"❌ Error with {provider_type} provider: {e}")


def main():
    """Run all conversation and vector search examples"""
    print("🚀 PersonaLab Conversation Recording & Vector Search Examples")
    print("=" * 60)
    
    try:
        example_1_basic_conversation_recording()
        example_2_semantic_conversation_search()
        example_3_conversation_detail_and_retrieval()
        example_4_embedding_providers()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("\n💡 Key Features Demonstrated:")
        print("   • Automatic conversation recording to database")
        print("   • Vector embeddings generation for semantic search") 
        print("   • Conversation history retrieval and management")
        print("   • Similarity-based conversation search")
        print("   • Support for multiple embedding providers")
        print("   • Integration with existing memory system")
        
        print("\n🔧 Available Embedding Providers:")
        print("   • 'simple' - Text feature-based (always available)")
        print("   • 'sentence-transformers' - Requires: pip install sentence-transformers")
        print("   • 'openai' - Requires OpenAI API key and: pip install openai")
        print("   • 'auto' - Automatically selects best available provider")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    main() 