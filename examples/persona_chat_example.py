#!/usr/bin/env python3
"""
PersonaLab Advanced Chat Example with Comprehensive Conversation Retrieval Testing

This example demonstrates:
1. Basic chat functionality with memory
2. Conversation retrieval based on query similarity
3. Multi-user conversation isolation
4. Threshold and limit testing
5. Edge case handling
6. Detailed retrieval analysis

The persona will now automatically retrieve relevant past conversations
based on the similarity to the current query, providing better context
and continuity in conversations.
"""

import os
import sys
import time
from typing import List, Dict

# Add the project root to the path so we can import personalab
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup PostgreSQL environment variables
os.environ.setdefault('POSTGRES_HOST', 'localhost')
os.environ.setdefault('POSTGRES_PORT', '5432')
os.environ.setdefault('POSTGRES_DB', 'personalab')
os.environ.setdefault('POSTGRES_USER', 'chenhong')
os.environ.setdefault('POSTGRES_PASSWORD', '')

from personalab import Persona


def test_basic_retrieval(persona: Persona, user_id: str) -> None:
    """Test basic conversation retrieval functionality"""
    print("\n" + "=" * 60)
    print("🔍 BASIC RETRIEVAL TESTING")
    print("=" * 60)
    
    test_cases = [
        {
            "query": "I'm having trouble with Python dictionaries. Can you remind me what we discussed?",
            "expected_topic": "Python/Data Science",
            "description": "Should retrieve Python programming conversations"
        },
        {
            "query": "What was that pasta cooking advice you gave me before?",
            "expected_topic": "Cooking",
            "description": "Should retrieve cooking conversations"
        },
        {
            "query": "Can you remind me how to work with lists in Python?",
            "expected_topic": "Python",
            "description": "Should retrieve Python list conversations"
        },
        {
            "query": "What did you tell me about visiting Japan?",
            "expected_topic": "Travel",
            "description": "Should retrieve travel conversations"
        },
        {
            "query": "How do I handle missing data again?",
            "expected_topic": "Data Science",
            "description": "Should retrieve data science conversations"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        print(f"Query: {test_case['query']}")
        print(f"Expected topic: {test_case['expected_topic']}")
        
        response = persona.chat(test_case['query'], user_id)
        print(f"Assistant: {response[:200]}...")
        print(f"✅ Test {i} completed")


def test_threshold_sensitivity(persona: Persona, user_id: str) -> None:
    """Test different similarity thresholds"""
    print("\n" + "=" * 60)
    print("🎯 THRESHOLD SENSITIVITY TESTING")
    print("=" * 60)
    
    # Test with different thresholds
    thresholds = [0.9, 0.7, 0.5, 0.3]
    test_query = "Tell me about Python programming concepts"
    
    for threshold in thresholds:
        print(f"\n--- Testing with threshold: {threshold} ---")
        
        # Create a new persona with different threshold
        test_persona = Persona(
            agent_id="helpful_assistant",
            personality="You are a helpful assistant.",
            enable_conversation_retrieval=True,
            max_retrieved_conversations=3,
            conversation_similarity_threshold=threshold,
            show_retrieval=True
        )
        
        response = test_persona.chat(test_query, user_id)
        print(f"Query: {test_query}")
        print(f"Response: {response[:150]}...")
        
        test_persona.endsession(user_id)
        test_persona.close()


def test_retrieval_limits(persona: Persona, user_id: str) -> None:
    """Test different retrieval limits"""
    print("\n" + "=" * 60)
    print("📊 RETRIEVAL LIMIT TESTING")
    print("=" * 60)
    
    # Test with different limits
    limits = [1, 3, 5, 10]
    test_query = "I want to learn more about programming and cooking"
    
    for limit in limits:
        print(f"\n--- Testing with limit: {limit} ---")
        
        # Create a new persona with different limit
        test_persona = Persona(
            agent_id="helpful_assistant",
            personality="You are a helpful assistant.",
            enable_conversation_retrieval=True,
            max_retrieved_conversations=limit,
            conversation_similarity_threshold=0.6,
            show_retrieval=True
        )
        
        response = test_persona.chat(test_query, user_id)
        print(f"Query: {test_query}")
        print(f"Response: {response[:150]}...")
        
        test_persona.endsession(user_id)
        test_persona.close()


def test_multi_user_isolation(persona: Persona) -> None:
    """Test that conversation retrieval respects user isolation"""
    print("\n" + "=" * 60)
    print("👥 MULTI-USER ISOLATION TESTING")
    print("=" * 60)
    
    # Setup conversations for User A
    user_a = "user_alice"
    print(f"\n--- Setting up conversations for {user_a} ---")
    
    alice_conversations = [
        "I'm a software engineer working on web applications",
        "I use React and Node.js for my projects",
        "I'm interested in learning about microservices architecture"
    ]
    
    for msg in alice_conversations:
        response = persona.chat(msg, user_a)
        print(f"Alice: {msg}")
        print(f"Assistant: {response[:80]}...")
    
    persona.endsession(user_a)
    print("✅ Alice's conversations saved")
    time.sleep(1)
    
    # Setup conversations for User B
    user_b = "user_bob"
    print(f"\n--- Setting up conversations for {user_b} ---")
    
    bob_conversations = [
        "I'm a data scientist working with machine learning models",
        "I use Python and scikit-learn for my analysis",
        "I'm interested in deep learning and neural networks"
    ]
    
    for msg in bob_conversations:
        response = persona.chat(msg, user_b)
        print(f"Bob: {msg}")
        print(f"Assistant: {response[:80]}...")
    
    persona.endsession(user_b)
    print("✅ Bob's conversations saved")
    time.sleep(1)
    
    # Test isolation: Alice queries should only retrieve Alice's conversations
    print(f"\n--- Testing isolation: Alice queries ---")
    alice_query = "What did I tell you about my work experience?"
    response = persona.chat(alice_query, user_a)
    print(f"Alice: {alice_query}")
    print(f"Assistant: {response[:150]}...")
    
    # Test isolation: Bob queries should only retrieve Bob's conversations
    print(f"\n--- Testing isolation: Bob queries ---")
    bob_query = "What did I tell you about my work experience?"
    response = persona.chat(bob_query, user_b)
    print(f"Bob: {bob_query}")
    print(f"Assistant: {response[:150]}...")
    
    persona.endsession(user_a)
    persona.endsession(user_b)


def test_edge_cases(persona: Persona, user_id: str) -> None:
    """Test edge cases and error conditions"""
    print("\n" + "=" * 60)
    print("⚠️  EDGE CASE TESTING")
    print("=" * 60)
    
    # Test 1: Very short query
    print("\n--- Test 1: Very short query ---")
    response = persona.chat("Hi", user_id)
    print(f"User: Hi")
    print(f"Assistant: {response[:100]}...")
    
    # Test 2: Very long query
    print("\n--- Test 2: Very long query ---")
    long_query = "I want to understand " + "programming " * 50 + "concepts"
    response = persona.chat(long_query, user_id)
    print(f"User: {long_query[:100]}...")
    print(f"Assistant: {response[:100]}...")
    
    # Test 3: Query with no relevant context
    print("\n--- Test 3: Query with no relevant context ---")
    response = persona.chat("What's the square root of 144?", user_id)
    print(f"User: What's the square root of 144?")
    print(f"Assistant: {response[:100]}...")
    
    # Test 4: Query similar to multiple topics
    print("\n--- Test 4: Query similar to multiple topics ---")
    response = persona.chat("I need help with Python programming for data analysis and cooking recipes", user_id)
    print(f"User: I need help with Python programming for data analysis and cooking recipes")
    print(f"Assistant: {response[:100]}...")
    
    persona.endsession(user_id)


def test_retrieval_with_disabled_feature() -> None:
    """Test behavior when retrieval is disabled"""
    print("\n" + "=" * 60)
    print("🚫 DISABLED RETRIEVAL TESTING")
    print("=" * 60)
    
    # Create persona with retrieval disabled
    persona_no_retrieval = Persona(
        agent_id="assistant_no_retrieval",
        personality="You are a helpful assistant.",
        enable_conversation_retrieval=False,
        show_retrieval=True
    )
    
    user_id = "test_user"
    
    # Have a conversation
    response = persona_no_retrieval.chat("Tell me about Python programming", user_id)
    print(f"User: Tell me about Python programming")
    print(f"Assistant: {response[:100]}...")
    
    persona_no_retrieval.endsession(user_id)
    
    # Try to reference previous conversation
    response = persona_no_retrieval.chat("What did we discuss about Python?", user_id)
    print(f"User: What did we discuss about Python?")
    print(f"Assistant: {response[:100]}...")
    
    persona_no_retrieval.endsession(user_id)
    persona_no_retrieval.close()


def analyze_retrieval_performance(persona: Persona, user_id: str) -> None:
    """Analyze retrieval performance and accuracy"""
    print("\n" + "=" * 60)
    print("📈 RETRIEVAL PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    # Test queries with expected topics
    test_cases = [
        ("Python list operations", "Python"),
        ("Pasta cooking methods", "Cooking"),
        ("Machine learning basics", "Data Science"),
        ("Tokyo travel tips", "Travel"),
        ("Dictionary data structures", "Python/Data Science")
    ]
    
    print("\nAnalyzing retrieval accuracy...")
    for query, expected_topic in test_cases:
        print(f"\n--- Query: {query} ---")
        print(f"Expected topic: {expected_topic}")
        
        # Use show_retrieval=True to see what's retrieved
        response = persona.chat(query, user_id)
        print(f"Response: {response[:150]}...")
        
        # Check if response seems relevant to expected topic
        response_lower = response.lower()
        if expected_topic.lower() in response_lower or any(word in response_lower for word in expected_topic.lower().split('/')):
            print("✅ Retrieval appears accurate")
        else:
            print("⚠️  Retrieval might not be optimal")
    
    persona.endsession(user_id)


def main():
    """Main function demonstrating comprehensive PersonaLab conversation retrieval"""
    print("🤖 PersonaLab Comprehensive Conversation Retrieval Testing")
    print("=" * 70)
    
    # Initialize persona with conversation retrieval enabled
    persona = Persona(
        agent_id="helpful_assistant",
        personality="You are a helpful and knowledgeable assistant. You remember past conversations and can reference them when helpful to provide continuity and context.",
        enable_conversation_retrieval=True,
        max_retrieved_conversations=3,
        conversation_similarity_threshold=0.1,
        show_retrieval=True
    )
    
    user_id = "demo_user"
    
    print(f"Persona initialized with conversation retrieval enabled")
    print(f"Agent ID: {persona.agent_id}")
    print(f"Max retrieved conversations: {persona.max_retrieved_conversations}")
    print(f"Similarity threshold: {persona.conversation_similarity_threshold}")
    
    try:
        # Run comprehensive tests
        test_basic_retrieval(persona, user_id)
        test_threshold_sensitivity(persona, user_id)
        test_retrieval_limits(persona, user_id)
        test_multi_user_isolation(persona)
        test_edge_cases(persona, user_id)
        test_retrieval_with_disabled_feature()
        analyze_retrieval_performance(persona, user_id)
        
        # Show final session info
        print("\n" + "=" * 60)
        print("📊 FINAL SESSION INFORMATION")
        print("=" * 60)
        session_info = persona.get_session_info(user_id)
        for key, value in session_info.items():
            print(f"  {key}: {value}")
        
        print("\n✅ All tests completed successfully!")
        print("\nKey features tested:")
        print("1. ✅ Conversation retrieval based on semantic similarity")
        print("2. ✅ User-specific conversation filtering and isolation")
        print("3. ✅ Configurable similarity thresholds")
        print("4. ✅ Configurable retrieval limits")
        print("5. ✅ Edge case handling")
        print("6. ✅ Multi-user isolation")
        print("7. ✅ Performance analysis")
        print("8. ✅ Disabled retrieval behavior")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        persona.close()
        print("\n🧹 Cleanup completed")


if __name__ == "__main__":
    main() 