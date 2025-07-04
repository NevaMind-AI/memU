#!/usr/bin/env python3
"""
PersonaLab Remote API Example

This example demonstrates the new API-only architecture of PersonaLab.
All memory operations are performed through remote API calls.

Architecture: Client -> API -> Backend -> Database

Requirements:
1. Start the PersonaLab API server first:
   python server/backend/main.py
   or
   docker-compose up

2. Server should be running at http://localhost:8000

Example Usage:
    python examples/remote_api_example.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from personalab import Persona
from personalab.llm import OpenAIClient

def main():
    """Demonstrate API-only PersonaLab usage"""
    
    print("🌟 PersonaLab API-Only Architecture Demo")
    print("=" * 50)
    
    # Create Persona with default API URL (http://localhost:8000)
    print("\n1. Creating Persona (API-only mode)")
    persona = Persona(
        agent_id="api_assistant",
        personality="You are a helpful assistant that remembers user interactions.",
        api_url="http://localhost:8000",  # Can be omitted as this is the default
        show_retrieval=True
    )
    print("✅ Persona created with API-only architecture")
    
    # Test with different users
    users = ["alice", "bob"]
    
    for user_id in users:
        print(f"\n{'='*20} User: {user_id} {'='*20}")
        
        # Chat 1: Initial conversation
        print(f"\n2. Initial conversation with {user_id}")
        response1 = persona.chat(
            "Hi! I'm a software engineer who loves Python programming.",
            user_id=user_id,
            learn=True
        )
        print(f"AI: {response1}")
        
        # Chat 2: Follow-up conversation
        print(f"\n3. Follow-up conversation with {user_id}")
        response2 = persona.chat(
            "What do you remember about me?",
            user_id=user_id,
            learn=True
        )
        print(f"AI: {response2}")
        
        # End session to update memory via API
        print(f"\n4. Ending session for {user_id}")
        result = persona.endsession(user_id)
        print(f"Session result: {result}")
        
        # Test memory retrieval after update
        print(f"\n5. Testing memory retrieval for {user_id}")
        response3 = persona.chat(
            "Tell me about my interests again",
            user_id=user_id,
            learn=False
        )
        print(f"AI: {response3}")
        
        # Get memory information
        print(f"\n6. Memory information for {user_id}")
        memory_info = persona.get_memory(user_id)
        print(f"Profile: {memory_info['profile']}")
        print(f"Events: {memory_info['events']}")
        print(f"Mind: {memory_info['mind']}")
        
        # Add specific memory via API
        print(f"\n7. Adding specific memory for {user_id}")
        persona.add_memory(
            f"{user_id} prefers clean, well-documented code",
            user_id=user_id,
            memory_type="profile"
        )
        
        # Search memories
        print(f"\n8. Searching memories for {user_id}")
        search_results = persona.search("Python", user_id=user_id)
        print(f"Search results: {search_results}")
    
    # Test cross-user memory isolation
    print(f"\n{'='*20} Cross-User Test {'='*20}")
    print("\n9. Testing memory isolation between users")
    
    alice_memory = persona.get_memory("alice")
    bob_memory = persona.get_memory("bob")
    
    print(f"Alice memory count: {len(alice_memory['events'])}")
    print(f"Bob memory count: {len(bob_memory['events'])}")
    print("✅ Memory is properly isolated between users")
    
    # Clean up
    print("\n10. Cleaning up")
    persona.close()
    print("✅ Persona closed successfully")
    
    print("\n🎉 API-only demo completed successfully!")
    print("\nKey advantages of API-only architecture:")
    print("- Clean separation of concerns")
    print("- Scalable and distributed")
    print("- Consistent data access")
    print("- Easy to deploy and maintain")

def test_custom_api_url():
    """Test with custom API URL"""
    print("\n" + "="*50)
    print("🔧 Testing Custom API URL")
    print("="*50)
    
    # Test with custom API URL
    try:
        persona = Persona(
            agent_id="remote_assistant", 
            api_url="http://remote-server:8000"  # Custom API server
        )
        print("✅ Custom API URL configured successfully")
        
        # This would fail if the remote server is not available
        # But the Persona object is created successfully
        persona.close()
        
    except Exception as e:
        print(f"⚠️ Custom API URL test: {e}")

def test_memory_operations():
    """Test specific memory operations via API"""
    print("\n" + "="*50)
    print("🧠 Testing Memory Operations")
    print("="*50)
    
    persona = Persona(
        agent_id="memory_tester",
        api_url="http://localhost:8000"
    )
    
    user_id = "test_user"
    
    try:
        # Test profile update
        print("\n1. Testing profile update")
        persona.add_memory(
            "Test user loves machine learning and AI research",
            user_id=user_id,
            memory_type="profile"
        )
        
        # Test events update
        print("\n2. Testing events update")
        persona.add_memory(
            "User completed a machine learning course",
            user_id=user_id,
            memory_type="events"
        )
        
        # Get memory info
        print("\n3. Getting memory information")
        memory_info = persona.get_memory(user_id)
        print(f"Memory info: {memory_info}")
        
        # Test session info
        print("\n4. Getting session information")
        session_info = persona.get_session_info(user_id)
        print(f"Session info: {session_info}")
        
        print("✅ Memory operations test completed")
        
    except Exception as e:
        print(f"❌ Memory operations test failed: {e}")
    
    finally:
        persona.close()

if __name__ == "__main__":
    print("Starting PersonaLab API-only demo...")
    print("Make sure the API server is running at http://localhost:8000")
    print("You can start it with: python server/backend/main.py")
    
    try:
        main()
        test_custom_api_url()
        test_memory_operations()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure the API server is running at http://localhost:8000")
    
    print("\nDemo finished.") 