#!/usr/bin/env python3
"""
Test script for MemU self-hosted server

This script demonstrates how to use the MemU server API.
"""

import json
import requests
import time

# Server configuration
SERVER_BASE_URL = "http://localhost:8000"

# Disable proxy for localhost connections
PROXIES = {
    'http': None,
    'https': None
}


def test_health_check():
    """Test server health"""
    print("🔍 Testing server health...")
    
    response = requests.get(f"{SERVER_BASE_URL}/health", proxies=PROXIES)
    if response.status_code == 200:
        print("✅ Server is healthy")
        print(f"   Response: {response.json()}")
    else:
        print("❌ Server health check failed")
        return False
    
    return True


def test_memorize_conversation():
    """Test memorization API"""
    print("\n📝 Testing conversation memorization...")
    
    # Prepare test data
    test_data = {
        "conversation_text": "User: Hello! How are you today?\nAssistant: I'm doing great, thank you for asking! How can I help you today?\nUser: I'm working on a Python project and need some help with APIs.\nAssistant: I'd be happy to help! What specifically would you like to know about APIs?",
        "user_id": "test_user_123",
        "user_name": "Test User",
        "agent_id": "test_agent_456",
        "agent_name": "Test Assistant"
    }
    
    # Start memorization
    response = requests.post(
        f"{SERVER_BASE_URL}/api/v1/memory/memorize",
        json=test_data,
        headers={"Content-Type": "application/json"},
        proxies=PROXIES
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Memorization started successfully")
        print(f"   Task ID: {result['task_id']}")
        print(f"   Status: {result['status']}")
        return result['task_id']
    else:
        print("❌ Memorization failed")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def test_task_status(task_id):
    """Test task status API"""
    print(f"\n⏳ Checking task status for {task_id}...")
    
    max_attempts = 200  # Wait up to 30 seconds
    for attempt in range(max_attempts):
        response = requests.get(f"{SERVER_BASE_URL}/api/v1/memory/memorize/status/{task_id}", proxies=PROXIES)
        
        if response.status_code == 200:
            result = response.json()
            status = result['status']
            print(f"   Attempt {attempt + 1}: Status = {status}")
            
            if status == "SUCCESS":
                print("✅ Task completed successfully")
                print(f"   Result: {json.dumps(result.get('result', {}), indent=2)}")
                return True
            elif status == "FAILURE":
                print("❌ Task failed")
                print(f"   Error: {result.get('error')}")
                return False
            elif status in ["PENDING", "PROCESSING"]:
                time.sleep(2)  # Wait 1 second before next check
                continue
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return False
    
    print("⚠️ Task did not complete within timeout")
    return False


def test_default_categories():
    """Test default categories API"""
    print("\n📂 Testing default categories retrieval...")
    
    test_data = {
        "user_id": "test_user_123",
        "agent_id": "test_agent_456",
        "include_inactive": False
    }
    
    response = requests.post(
        f"{SERVER_BASE_URL}/api/v1/memory/retrieve/default-categories",
        json=test_data,
        headers={"Content-Type": "application/json"},
        proxies=PROXIES
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Default categories retrieved successfully")
        print(f"   Total categories: {result['total_categories']}")
        for category in result['categories']:
            print(f"   - {category['name']}: {category['memory_count']} memories")
        return True
    else:
        print("❌ Default categories retrieval failed")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_related_memory_items():
    """Test related memory items API"""
    print("\n🔍 Testing related memory items search...")
    
    test_data = {
        "user_id": "test_user_123",
        "agent_id": "test_agent_456",
        "query": "Python programming help",
        "top_k": 5,
        "min_similarity": 0.3
    }
    
    response = requests.post(
        f"{SERVER_BASE_URL}/api/v1/memory/retrieve/related-memory-items",
        json=test_data,
        headers={"Content-Type": "application/json"},
        proxies=PROXIES
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Related memory items retrieved successfully")
        print(f"   Query: {result['query']}")
        print(f"   Total found: {result['total_found']}")
        for i, memory in enumerate(result['related_memories'][:3]):  # Show first 3
            print(f"   {i+1}. Score: {memory['similarity_score']:.3f}")
            print(f"      Content: {memory['memory']['content'][:100]}...")
        return True
    else:
        print("❌ Related memory items retrieval failed")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_related_clustered_categories():
    """Test related clustered categories API"""
    print("\n🗂️ Testing related clustered categories search...")
    
    test_data = {
        "user_id": "test_user_123",
        "agent_id": "test_agent_456",
        "category_query": "programming assistance",
        "top_k": 3,
        "min_similarity": 0.3
    }
    
    response = requests.post(
        f"{SERVER_BASE_URL}/api/v1/memory/retrieve/related-clustered-categories",
        json=test_data,
        headers={"Content-Type": "application/json"},
        proxies=PROXIES
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Related clustered categories retrieved successfully")
        print(f"   Query: {result['category_query']}")
        print(f"   Total categories found: {result['total_categories_found']}")
        for category in result['clustered_categories']:
            print(f"   - {category['name']}: Score {category['similarity_score']:.3f}, {category['memory_count']} memories")
        return True
    else:
        print("❌ Related clustered categories retrieval failed")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def main():
    """Run all tests"""
    print("🚀 MemU Server API Test")
    print("=" * 50)
    
    # Test server health
    if not test_health_check():
        print("\n❌ Server is not responding. Make sure the server is running on port 8000")
        return
    
    # Test memorization
    task_id = test_memorize_conversation()
    if not task_id:
        print("\n❌ Cannot proceed without successful memorization")
        return
    
    # Wait for task completion
    if not test_task_status(task_id):
        print("\n⚠️ Memorization task did not complete, but continuing with other tests")
    
    # Give the system a moment to process
    time.sleep(2)
    
    # Test retrieval APIs
    test_default_categories()
    test_related_memory_items()
    test_related_clustered_categories()
    
    print("\n🎉 Test completed!")
    print("\nNext steps:")
    print("1. Check the ./memory directory for generated files")
    print("2. Try the interactive API docs at http://localhost:8000/docs")
    print("3. Integrate with your applications using the MemU SDK")


if __name__ == "__main__":
    main()
