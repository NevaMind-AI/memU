"""
Test script to verify MemU + OpenClaw bridge connection
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import configuration
from config import SERVICE_CONFIG

def test_basic_connection():
    """Test basic connectivity to the bridge"""
    print("Testing basic bridge connectivity...")
    
    import requests
    import json
    
    # Test the chat completions endpoint
    test_data = {
        'messages': [{'role': 'user', 'content': 'Hello, this is a test.'}],
        'model': 'openclaw-bridge'
    }
    
    try:
        response = requests.post('http://localhost:5000/v1/chat/completions', json=test_data, timeout=15)
        if response.status_code == 200:
            print("✅ Bridge connection successful")
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"   Got response (first 100 chars): {content[:100] if content else 'Empty'}")
            return True
        else:
            print(f"❌ Bridge connection failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bridge connection error: {e}")
        return False

def test_embeddings():
    """Test embeddings endpoint"""
    print("Testing embeddings endpoint...")
    
    import requests
    import json
    
    # Test the embeddings endpoint
    test_data = {
        'input': ['test embedding'],
        'model': 'fake-embeddings'
    }
    
    try:
        response = requests.post('http://localhost:5000/v1/embeddings', json=test_data, timeout=10)
        if response.status_code == 200:
            print("✅ Embeddings endpoint working")
            return True
        else:
            print(f"❌ Embeddings endpoint failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Embeddings endpoint error: {e}")
        return False

def test_memu_config():
    """Test if MemU configuration loads properly"""
    print("Testing MemU configuration...")
    
    try:
        from memu.app import MemoryService
        service = MemoryService(**SERVICE_CONFIG)
        print("✅ MemU configuration loaded successfully")
        return True
    except Exception as e:
        print(f"❌ MemU configuration error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_memorize_function():
    """Test the memorize function specifically"""
    print("Testing memorize function...")
    
    try:
        from memu.app import MemoryService
        service = MemoryService(**SERVICE_CONFIG)
        
        # Test basic memorize function with a simple text
        result = await service.memorize(
            resource_url="test://simple-test",
            modality="text",
            content="This is a test memory to store in the system."
        )
        
        print("✅ Memorize function working")
        print(f"   Created {len(result.get('items', []))} memory items")
        return True
    except Exception as e:
        print(f"❌ Memorize function error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("* Testing MemU + OpenClaw Integration")
    print("="*50)
    
    # Test individual components
    tests = [
        ("Bridge Connection", test_basic_connection),
        ("Embeddings Endpoint", test_embeddings),
        ("MemU Config", test_memu_config),
        ("Memorize Function", test_memorize_function),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTESTING {name}...")
        if name in ["Memorize Function"]:
            # Async function
            result = await test_func()
        else:
            # Sync function
            result = test_func()
        results.append((name, result))
    
    print(f"\nRESULTS:")
    print("-" * 30)
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name:<20} {status}")
        if not passed:
            all_passed = False
    
    print("="*50)
    if all_passed:
        print("SUCCESS! All tests passed! MemU + OpenClaw integration is working properly.")
    else:
        print("FAILURE! Some tests failed. Please check the configuration.")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())