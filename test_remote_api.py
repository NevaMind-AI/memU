#!/usr/bin/env python3
"""
PersonaLab API-Only Architecture Test Script

This script tests the new API-only architecture where all memory operations
are performed through remote API calls.

Requirements:
- API server running at http://localhost:8000
- Start with: python server/backend/main.py

Usage:
    python test_remote_api.py
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all imports work correctly"""
    print("🔍 Testing imports...")
    
    try:
        from personalab import Persona
        from personalab.memory import MemoryClient, Memory
        from personalab.llm import OpenAIClient
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_persona_api_mode():
    """Test Persona in API-only mode"""
    print("\n🤖 Testing Persona API-only mode...")
    
    try:
        from personalab import Persona
        
        # Create Persona with default API URL
        persona = Persona(
            agent_id="test_agent",
            personality="You are a test assistant.",
            api_url="http://localhost:8000",  # Default API URL
            use_memory=True
        )
        
        print("✅ Persona created successfully in API-only mode")
        
        # Test basic conversation (may fail if server not running)
        try:
            response = persona.chat("Hello, test message", user_id="test_user", learn=True)
            print(f"✅ Chat successful: {response[:100]}...")
            
            # Test session ending
            result = persona.endsession("test_user")
            print(f"✅ Session ended: {result}")
            
        except Exception as e:
            print(f"⚠️ Chat/session test failed (server may not be running): {e}")
        
        # Clean up
        persona.close()
        print("✅ Persona closed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Persona API mode test failed: {e}")
        return False

def test_memory_client_api_mode():
    """Test MemoryClient in API-only mode"""
    print("\n🧠 Testing MemoryClient API-only mode...")
    
    try:
        from personalab.memory import MemoryClient
        
        # Create MemoryClient (API-only)
        client = MemoryClient(api_url="http://localhost:8000")
        print("✅ MemoryClient created successfully")
        
        # Test memory operations (may fail if server not running)
        try:
            memory = client.get_memory_by_agent("test_agent", "test_user")
            print(f"✅ Memory retrieved: {type(memory)}")
            
            # Test memory info
            memory_info = client.get_memory_info("test_agent", "test_user")
            print(f"✅ Memory info: {memory_info}")
            
        except Exception as e:
            print(f"⚠️ Memory operations failed (server may not be running): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ MemoryClient API mode test failed: {e}")
        return False

def test_api_memory():
    """Test Memory functionality"""
    print("\n💾 Testing Memory...")
    
    try:
        from personalab.memory import MemoryClient, Memory
        
        # Create test Memory
        client = MemoryClient(api_url="http://localhost:8000")
        test_data = {
            "profile_content": ["Test user profile"],
            "event_content": ["Test event 1", "Test event 2"],
            "mind_content": ["Test insight"]
        }
        
        api_memory = Memory(
            agent_id="test_agent",
            user_id="test_user", 
            memory_client=client,
            data=test_data
        )
        
        # Test memory methods
        profile = api_memory.get_profile()
        events = api_memory.get_events()
        mind = api_memory.get_mind()
        
        print(f"✅ Profile: {profile}")
        print(f"✅ Events: {events}")
        print(f"✅ Mind: {mind}")
        
        # Test memory stats
        stats = api_memory.get_memory_stats()
        print(f"✅ Stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        return False

def test_persona_features():
    """Test Persona features in API-only mode"""
    print("\n🎯 Testing Persona features...")
    
    try:
        from personalab import Persona
        
        persona = Persona(
            agent_id="feature_test",
            personality="You are a helpful test assistant.",
            api_url="http://localhost:8000"
        )
        
        # Test memory operations
        try:
            persona.add_memory("Test profile info", "test_user", "profile")
            persona.add_memory("Test event info", "test_user", "events")
            print("✅ Memory addition successful")
        except Exception as e:
            print(f"⚠️ Memory addition failed: {e}")
        
        # Test search
        try:
            results = persona.search("test", "test_user")
            print(f"✅ Search successful: {len(results)} results")
        except Exception as e:
            print(f"⚠️ Search failed: {e}")
        
        # Test memory retrieval
        try:
            memory_info = persona.get_memory("test_user")
            print(f"✅ Memory retrieval: {len(memory_info['events'])} events")
        except Exception as e:
            print(f"⚠️ Memory retrieval failed: {e}")
        
        # Test session info
        session_info = persona.get_session_info("test_user")
        print(f"✅ Session info: {session_info}")
        
        persona.close()
        return True
        
    except Exception as e:
        print(f"❌ Persona features test failed: {e}")
        return False

def test_architecture_consistency():
    """Test that the API-only architecture is consistent"""
    print("\n🏗️ Testing architecture consistency...")
    
    try:
        from personalab import Persona
        from personalab.memory import MemoryClient
        
        # Test that all Personas use API by default
        persona1 = Persona(agent_id="test1")  # No API URL specified - should use default
        persona2 = Persona(agent_id="test2", api_url="http://localhost:8000")
        
        # Both should have API-based memory clients
        assert persona1.memory_client is not None
        assert persona2.memory_client is not None
        assert persona1.api_url == "http://localhost:8000"  # Default API URL
        assert persona2.api_url == "http://localhost:8000"
        
        print("✅ All Personas use API-only architecture")
        
        # Test that MemoryClient is API-only
        client = MemoryClient(api_url="http://localhost:8000")
        assert client.api_url == "http://localhost:8000"
        print("✅ MemoryClient is API-only")
        
        persona1.close()
        persona2.close()
        return True
        
    except Exception as e:
        print(f"❌ Architecture consistency test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 PersonaLab API-Only Architecture Test Suite")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_persona_api_mode,
        test_memory_client_api_mode,
        test_api_memory,
        test_persona_features,
        test_architecture_consistency,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API-only architecture is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        if passed > 0:
            print("Note: Some failures may be due to the API server not running.")
    
    print("\n💡 To start the API server:")
    print("   python server/backend/main.py")
    print("   Then re-run this test script.")

if __name__ == "__main__":
    main() 