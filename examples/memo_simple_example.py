"""
PersonaLab Memo Simple Example

Demonstrates the memo module for conversation recording and vector search
without requiring LLM API keys or complex memory processing.
"""

from personalab.memo import ConversationManager

def main():
    print("=== PersonaLab Memo Simple Example ===\n")
    
    # Initialize conversation manager with best available embeddings
    # Note: Set OPENAI_API_KEY environment variable to use OpenAI embeddings
    # Will automatically try OpenAI first, then SentenceTransformers if available
    
    print("Initializing ConversationManager with best available embeddings...")
    try:
        conversation_manager = ConversationManager(
            db_path="memo_simple_example.db",
            enable_embeddings=True,
            embedding_provider="auto"  # Auto-select best available provider
        )
        print("✅ Embedding provider initialized successfully")
    except Exception as e:
        print(f"❌ No embedding providers available: {e}")
        print("   Please install OpenAI or sentence-transformers library")
        print("   For OpenAI: pip install openai (and set OPENAI_API_KEY)")
        print("   For SentenceTransformers: pip install sentence-transformers")
        return
    
    agent_id = "demo_agent"
    
    # Example conversation 1: Introduction
    print("1. Recording introduction conversation...")
    conversation1 = [
        {"role": "user", "content": "Hi, I'm Alice. I'm 25 years old and I work as a software engineer."},
        {"role": "assistant", "content": "Nice to meet you, Alice! It's great to know you're a software engineer. What kind of projects do you typically work on?"},
        {"role": "user", "content": "I mainly work on web applications using Python and React. I love building user-friendly interfaces."},
        {"role": "assistant", "content": "That sounds really interesting! Python and React are excellent technologies for web development."}
    ]
    
    # Record conversation in memo system
    recorded_conv1 = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=conversation1,
        user_id="alice_123"  # Adding user ID for filtering
    )
    print(f"Conversation recorded: {recorded_conv1.conversation_id}")
    print(f"User ID: {recorded_conv1.user_id}")
    print(f"Summary: {recorded_conv1.summary}\n")
    
    # Example conversation 2: Hobby discussion
    print("2. Recording hobby conversation...")
    conversation2 = [
        {"role": "user", "content": "In my free time, I enjoy playing guitar and hiking in the mountains."},
        {"role": "assistant", "content": "Guitar and hiking are wonderful hobbies! How long have you been playing guitar?"},
        {"role": "user", "content": "I've been playing for about 8 years now. I love both acoustic and electric guitar."},
        {"role": "assistant", "content": "That's impressive! Eight years of experience must mean you're quite skilled."}
    ]
    
    recorded_conv2 = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=conversation2,
        user_id="alice_123"  # Same user as first conversation
    )
    print(f"Conversation recorded: {recorded_conv2.conversation_id}")
    print(f"User ID: {recorded_conv2.user_id}")
    print(f"Summary: {recorded_conv2.summary}\n")
    
    # Example conversation 3: Travel discussion
    print("3. Recording travel conversation...")
    conversation3 = [
        {"role": "user", "content": "I recently traveled to Japan and it was amazing. The culture and food were incredible."},
        {"role": "assistant", "content": "Japan sounds like it was a wonderful experience! What was your favorite part of the trip?"},
        {"role": "user", "content": "I loved visiting the temples in Kyoto and trying authentic ramen in Tokyo."},
        {"role": "assistant", "content": "Kyoto temples and Tokyo ramen - you experienced some of the best Japan has to offer!"}
    ]
    
    recorded_conv3 = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=conversation3,
        user_id="bob_456"  # Different user to demonstrate filtering
    )
    print(f"Conversation recorded: {recorded_conv3.conversation_id}")
    print(f"User ID: {recorded_conv3.user_id}")
    print(f"Summary: {recorded_conv3.summary}\n")
    
    # Search for similar conversations
    print("4. Searching similar conversations:")
    
    # Search for music-related conversations
    print("\nSearching for 'music guitar'...")
    music_results = conversation_manager.search_similar_conversations(
        agent_id=agent_id,
        query="music guitar playing",
        limit=5,
        similarity_threshold=0.1
    )
    
    for i, result in enumerate(music_results, 1):
        print(f"  {i}. Score: {result['similarity_score']:.3f}")
        print(f"     Summary: {result['summary']}")
        print(f"     Content: {result['matched_content'][:100]}...")
        print()
    
    # Search for travel-related conversations
    print("Searching for 'travel Japan'...")
    travel_results = conversation_manager.search_similar_conversations(
        agent_id=agent_id,
        query="travel Japan culture",
        limit=5,
        similarity_threshold=0.1
    )
    
    for i, result in enumerate(travel_results, 1):
        print(f"  {i}. Score: {result['similarity_score']:.3f}")
        print(f"     Summary: {result['summary']}")
        print(f"     Content: {result['matched_content'][:100]}...")
        print()
    
    # Get conversation history
    print("5. Conversation History:")
    print("All conversations:")
    history = conversation_manager.get_conversation_history(agent_id, limit=10)
    
    for i, conv in enumerate(history, 1):
        print(f"  {i}. ID: {conv['conversation_id'][:8]}...")
        print(f"     Created: {conv['created_at']}")
        print(f"     User ID: {conv.get('user_id', 'N/A')}")
        print(f"     Turns: {conv['turn_count']}")
        print(f"     Summary: {conv['summary']}")
        print()
    
    # Filter by user_id
    print("Conversations for user alice_123:")
    alice_history = conversation_manager.get_conversation_history(
        agent_id, 
        limit=10, 
        user_id="alice_123"
    )
    
    for i, conv in enumerate(alice_history, 1):
        print(f"  {i}. ID: {conv['conversation_id'][:8]}...")
        print(f"     User ID: {conv.get('user_id', 'N/A')}")
        print(f"     Summary: {conv['summary']}")
        print()
    
    print("Conversations for user bob_456:")
    bob_history = conversation_manager.get_conversation_history(
        agent_id, 
        limit=10, 
        user_id="bob_456"
    )
    
    for i, conv in enumerate(bob_history, 1):
        print(f"  {i}. ID: {conv['conversation_id'][:8]}...")
        print(f"     User ID: {conv.get('user_id', 'N/A')}")
        print(f"     Summary: {conv['summary']}")
        print()
    
    # Get conversation statistics
    print("6. Statistics:")
    conversation_stats = conversation_manager.get_conversation_stats(agent_id)
    print("Conversation Stats:")
    for key, value in conversation_stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Get detailed conversation
    print("7. Detailed Conversation Example:")
    if history:
        first_conv_id = history[0]['conversation_id']
        detailed_conv = conversation_manager.get_conversation(first_conv_id)
        
        if detailed_conv:
            print(f"Conversation ID: {detailed_conv.conversation_id}")
            print(f"Agent ID: {detailed_conv.agent_id}")
            print(f"Created: {detailed_conv.created_at}")
            print(f"Turn Count: {detailed_conv.turn_count}")
            print(f"Messages:")
            
            for i, message in enumerate(detailed_conv.messages, 1):
                print(f"  {i}. {message.role}: {message.content}")
            print()
    
    # Session-based conversation tracking
    print("8. Session-based Tracking:")
    session_id = "session_123"
    
    # Record a conversation with session ID
    session_conversation = [
        {"role": "user", "content": "This is a conversation in a specific session."},
        {"role": "assistant", "content": "I understand this is part of session_123."}
    ]
    
    session_conv = conversation_manager.record_conversation(
        agent_id=agent_id,
        messages=session_conversation,
        session_id=session_id,
        user_id="charlie_789"  # Another user for session demo
    )
    
    print(f"Session conversation recorded: {session_conv.conversation_id}")
    
    # Get conversations for specific session
    session_history = conversation_manager.get_conversation_history(
        agent_id, 
        limit=10, 
        session_id=session_id
    )
    
    print(f"Conversations in session {session_id}:")
    for conv in session_history:
        print(f"  - {conv['conversation_id'][:8]}... : {conv['summary']}")
    print()
    
    print("=== Example completed successfully! ===")
    print("\nThe memo module provides:")
    print("- Standalone conversation recording and storage")
    print("- High-quality vector embeddings for semantic similarity search") 
    print("- Session-based conversation organization")
    print("- User-based conversation filtering")
    print("- Multiple embedding provider support (OpenAI, SentenceTransformers)")
    print("- Automatic provider selection for best performance")
    print("- Simple API for conversation management")

if __name__ == "__main__":
    main() 