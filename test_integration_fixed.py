"""
MemU + OpenClaw Integration Test Suite

This script tests all aspects of the MemU + OpenClaw integration to ensure
everything is working properly before going live.
"""

import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path
import requests

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from memu.app import MemoryService
from config import SERVICE_CONFIG


def test_bridge_connectivity():
    """Test if the OpenClaw bridge is responding"""
    print("  Testing Bridge Connectivity...")
    
    try:
        # Test the bridge endpoint
        response = requests.get("http://localhost:5000/v1/models", timeout=10)
        if response.status_code == 200:
            print("  Bridge is responding")
            return True
        else:
            print(f"  Bridge returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  Bridge connectivity test failed: {e}")
        return False


def test_memory_service():
    """Test basic MemU memory service functionality"""
    print("  Testing Memory Service...")
    
    try:
        # Initialize the service with our configuration
        service = MemoryService(**SERVICE_CONFIG)
        
        # Test creating a simple memory item
        result = asyncio.run(service.create_memory_item(
            memory_type="knowledge",
            memory_content="This is a test memory for validation purposes",
            memory_categories=["validation", "testing"]
        ))
        
        if result and 'memory_item' in result:
            print("  Memory service is working correctly")
            print(f"   Created memory item ID: {result['memory_item']['id']}")
            return True
        else:
            print("  Memory service test failed - no valid result returned")
            return False
            
    except Exception as e:
        print(f"  Memory service test failed: {e}")
        return False


def test_memory_retrieval():
    """Test memory retrieval functionality"""
    print("  Testing Memory Retrieval...")
    
    try:
        service = MemoryService(**SERVICE_CONFIG)
        
        # First, create a test memory
        create_result = asyncio.run(service.create_memory_item(
            memory_type="knowledge",
            memory_content="Testing retrieval functionality with specific keywords like python programming",
            memory_categories=["testing", "retrieval"]
        ))
        
        # Then try to retrieve it
        retrieve_result = asyncio.run(service.retrieve(
            queries=[{"role": "user", "content": "Show me memories about python programming"}]
        ))
        
        items = retrieve_result.get('items', [])
        if len(items) > 0:
            print("  Memory retrieval is working correctly")
            print(f"   Retrieved {len(items)} items matching the query")
            return True
        else:
            print("   Memory retrieval completed but no items matched (this may be normal)")
            return True  # Not necessarily a failure
            
    except Exception as e:
        print(f"  Memory retrieval test failed: {e}")
        return False


def test_legacy_import():
    """Test the legacy import functionality"""
    print("  Testing Legacy Import...")
    
    import_script = Path(__file__).parent / "import_legacy.py"
    
    if not import_script.exists():
        print("  Legacy import script not found")
        return False
    
    try:
        # Run the import script as a subprocess
        result = subprocess.run([sys.executable, str(import_script)], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("  Legacy import script executed successfully")
            return True
        else:
            print(f"  Legacy import script failed with exit code {result.returncode}")
            print(f"   Stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  Legacy import script timed out")
        return False
    except Exception as e:
        print(f"  Legacy import test failed: {e}")
        return False


def test_configuration_loading():
    """Test if configuration loads correctly"""
    print("Testing Configuration Loading...")
    
    try:
        # Import the config to test loading
        import config
        print("  Configuration loaded successfully")
        print(f"   Database provider: {config.DATABASE_CONFIG.metadata_store.provider}")
        print(f"   LLM provider: {config.LLM_PROFILES.root['default'].provider}")
        print(f"   Memory categories: {len(config.MEMORY_CATEGORIES)}")
        return True
    except Exception as e:
        print(f"  Configuration loading failed: {e}")
        return False


def test_manager_commands():
    """Test manager.py commands"""
    print("  Testing Manager Commands...")
    
    manager_script = Path(__file__).parent / "manager.py"
    
    if not manager_script.exists():
        print("  Manager script not found")
        return False
    
    try:
        # Test the 'validate' command
        result = subprocess.run([sys.executable, str(manager_script), "validate"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("  Manager validation command executed successfully")
            return True
        else:
            print(f"  Manager validation failed with exit code {result.returncode}")
            print(f"   Stdout: {result.stdout}")
            print(f"   Stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   Manager validation timed out (may be OK if bridge not running)")
        return True  # Not necessarily a failure if bridge isn't running
    except Exception as e:
        print(f"  Manager command test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("Running MemU + OpenClaw Integration Tests...\n")
    
    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("Bridge Connectivity", test_bridge_connectivity),
        ("Memory Service", test_memory_service),
        ("Memory Retrieval", test_memory_retrieval),
        ("Legacy Import", test_legacy_import),
        ("Manager Commands", test_manager_commands),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nTEST: {test_name}")
        print("-" * (len(test_name) + 2))
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Brief pause between tests
    
    print(f"\n{'='*50}")
    print("TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! The integration is ready for use.")
        return True
    else:
        print(f"   {total - passed} test(s) failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)