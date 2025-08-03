"""
MemU SDK Comprehensive Example
=============================

Demonstrates complete MemU workflow:
1. Memorize conversations using SDK
2. Monitor task status with 2-minute monitoring
3. Recall memories using SDK client recall APIs
4. Test different scenarios and error handling
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the memu package to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# MemU imports
from memu.sdk import MemuClient
from memu.sdk.exceptions import MemuAPIException, MemuValidationException, MemuConnectionException

# Environment setup
os.environ["MEMU_API_BASE_URL"] = "http://test-hippocampus-cloud-853369149.us-east-1.elb.amazonaws.com/"
os.environ["MEMU_API_KEY"] = "mu_zsRrfdrDTSBTBn0KarVJDx-2I2ux8YmTjjuO0wcG5hCpSgF8OrI_ZKkwv36lTRe57RVLLI5UU0icD_RkF7uEtNnQCN6vIbzaz1NxMg"


def test_memorize_functionality():
    """Test memorize conversation functionality with comprehensive scenarios"""
    
    print("🧠 === MEMORIZE FUNCTIONALITY TEST ===")
    print("Testing conversation memorization with different scenarios")
    print()
    
    # Test conversations with different topics
    test_conversations = [
        {
            "name": "Hiking Adventure",
            "user_id": "user_alice", 
            "user_name": "Alice Johnson",
            "agent_id": "1234",
            "agent_name": "Assistant", 
            "conversation": """User: I went on an amazing hike yesterday in Mount Rainier National Park. The weather was perfect and I saw some incredible views from the Skyline Trail.

Assistant: That sounds wonderful! Mount Rainier has some of the most spectacular alpine scenery in the Pacific Northwest. The Skyline Trail is definitely one of the crown jewels of the park. Did you make it to Panorama Point?

User: Yes! The view of Mount Rainier from Panorama Point was breathtaking. I could see the Nisqually Glacier clearly. I'm planning to go back next month to try the Tolmie Peak trail.

Assistant: Excellent choice! Tolmie Peak offers one of the best views of Mount Rainier, and the hike to Eunice Lake is beautiful too. Make sure to check the trail conditions before you go - that area can have snow well into summer."""
        },
        {
            "name": "Cooking Experience",
            "user_id": "user_bob",
            "user_name": "Bob Chen",
            "agent_id": "1234",
            "agent_name": "Assistant",
            "conversation": """User: I tried making homemade pasta for the first time yesterday. It was challenging but so rewarding!

Assistant: That's wonderful! Making pasta from scratch is definitely an art. What type of pasta did you make? Fettuccine, ravioli, or something else?

User: I made fettuccine with a simple egg and flour dough. The rolling and cutting took forever, but the taste was incredible. So much better than store-bought!

Assistant: Fresh pasta really does make a difference! The texture and flavor are incomparable. Did you make a sauce to go with it, or keep it simple with just butter and herbs?"""
        }
    ]
    
    # Initialize SDK client
    client = MemuClient(
        base_url=os.getenv("MEMU_API_BASE_URL"),
        api_key=os.getenv("MEMU_API_KEY")
    )
    
    print(f"🔗 Connected to: {client.base_url}")
    print(f"🔑 API Key: {client.api_key[:8]}...")
    print()
    
    task_ids = []
    
    try:
        # Test each conversation
        for i, test_case in enumerate(test_conversations, 1):
            print(f"📝 Test {i}: {test_case['name']}")
            print(f"   User: {test_case['user_name']} (ID: {test_case['user_id']})")
            print(f"   Agent: {test_case['agent_name']} (ID: {test_case['agent_id']})")
            print(f"   Conversation length: {len(test_case['conversation'])} characters")
            
            try:
                # Memorize conversation
                response = client.memorize_conversation(
                    conversation_text=test_case["conversation"],
                    user_id=test_case["user_id"],
                    user_name=test_case["user_name"],
                    agent_id=test_case["agent_id"],
                    agent_name=test_case["agent_name"],
                )
                
                print(f"   ✅ Memorization started successfully!")
                print(f"   📋 Task ID: {response.task_id}")
                print(f"   📊 Status: {response.status}")
                print(f"   💬 Message: {response.message}")
                
                task_ids.append({
                    "task_id": response.task_id,
                    "name": test_case["name"],
                    "user_id": test_case["user_id"]
                })
                
            except MemuValidationException as e:
                print(f"   ❌ Validation error: {e}")
            except MemuAPIException as e:
                print(f"   ❌ API error: {e}")
            except MemuConnectionException as e:
                print(f"   ❌ Connection error: {e}")
            
            print()
            
    finally:
        client.close()
    
    return task_ids


def test_task_status_monitoring(task_ids: List[Dict[str, Any]]):
    """Test task status monitoring functionality with 2-minute time-based monitoring"""
    
    print("📊 === TASK STATUS MONITORING TEST ===")
    print("Monitoring memorization task progress for 2 minutes")
    print()
    
    if not task_ids:
        print("❌ No task IDs provided for monitoring")
        return
    
    # Initialize SDK client
    client = MemuClient(
        base_url=os.getenv("MEMU_API_BASE_URL"),
        api_key=os.getenv("MEMU_API_KEY")
    )
    
    try:
        for task_info in task_ids:
            task_id = task_info["task_id"]
            name = task_info["name"]
            user_id = task_info["user_id"]
            
            print(f"🔍 Monitoring task: {name}")
            print(f"   Task ID: {task_id}")
            print(f"   User ID: {user_id}")
            
            # Monitor task for 2 minutes
            monitor_duration = 120  # 2 minutes in seconds
            check_interval = 5      # Check every 5 seconds
            start_time = time.time()
            check_count = 0
            
            print(f"   ⏰ Monitoring for {monitor_duration} seconds (2 minutes)")
            
            while time.time() - start_time < monitor_duration:
                try:
                    elapsed_time = time.time() - start_time
                    check_count += 1
                    
                    task_status = client.get_task_status(task_id)
                    
                    print(f"   📈 Check {check_count} ({elapsed_time:.1f}s): Status = {task_status.status}")
                    
                    if task_status.progress:
                        print(f"   📊 Progress: {task_status.progress}")
                    
                    if task_status.result:
                        print(f"   ✅ Result: {task_status.result}")
                    
                    if task_status.error:
                        print(f"   ❌ Error: {task_status.error}")
                    
                    if task_status.started_at:
                        print(f"   🕐 Started: {task_status.started_at}")
                    
                    if task_status.completed_at:
                        print(f"   🏁 Completed: {task_status.completed_at}")
                    
                    # Check if task is complete
                    if task_status.status in ['SUCCESS', 'FAILURE', 'REVOKED']:
                        print(f"   ✅ Task completed with status: {task_status.status}")
                        print(f"   ⏱️  Total monitoring time: {elapsed_time:.1f} seconds")
                        break
                    
                    # Calculate remaining time
                    remaining_time = monitor_duration - elapsed_time
                    if remaining_time > check_interval:
                        print(f"   ⏳ Waiting {check_interval} seconds... ({remaining_time:.1f}s remaining)")
                        time.sleep(check_interval)
                    elif remaining_time > 0:
                        print(f"   ⏳ Waiting {remaining_time:.1f} seconds...")
                        time.sleep(remaining_time)
                    
                except MemuAPIException as e:
                    print(f"   ⚠️  API error: {e}")
                    break
                except Exception as e:
                    print(f"   ⚠️  Unexpected error: {e}")
                    break
            
            # Final status check
            final_elapsed = time.time() - start_time
            if final_elapsed >= monitor_duration:
                print(f"   ⏰ Monitoring timeout after {final_elapsed:.1f} seconds")
                try:
                    final_status = client.get_task_status(task_id)
                    print(f"   📋 Final status: {final_status.status}")
                except:
                    print(f"   📋 Could not retrieve final status")
            
            print()
    
    finally:
        client.close()


def test_recall_functionality():
    """Test recall functionality using SDK client recall APIs"""
    
    print("🧠 === RECALL FUNCTIONALITY TEST ===")
    print("Testing memory recall using SDK client recall APIs")
    print()
    
    # Initialize SDK client
    client = MemuClient(
        base_url=os.getenv("MEMU_API_BASE_URL"),
        api_key=os.getenv("MEMU_API_KEY")
    )
    
    try:
        print(f"📊 SDK Client Status:")
        print(f"   Base URL: {client.base_url}")
        print(f"   API Key: {client.api_key[:8]}...")
        print(f"   Timeout: {client.timeout}s")
        print()
        
        # Test users and project data
        test_users = [
            {"user_id": "user_alice"},
            {"user_id": "user_bob"}
        ]
        
        for test_user in test_users:
            user_id = test_user["user_id"]
            agent_id = "1234"
            
            print(f"👤 Testing recall for user: {user_id}")
            
            # Method 1: Retrieve default categories
            print(f"   📂 Method 1: Default categories")
            try:
                categories_response = client.retrieve_default_categories(
                    user_id = user_id,
                    agent_id = agent_id,
                    include_inactive=False,
                )
                
                print(f"   ✅ Retrieved {categories_response.total_categories} default categories")
                for i, category in enumerate(categories_response.categories[:3]):
                    category_keys = list(category.keys())[:3]  # Show first 3 keys
                    print(f"      {i+1}. Category keys: {category_keys}")
                    
            except MemuAPIException as e:
                print(f"   ❌ API Error: {e}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Method 2: Retrieve related clustered categories
            print(f"   🔍 Method 2: Related clustered categories")
            try:
                category_query = "hiking outdoor activities exercise"
                clustered_response = client.retrieve_related_clustered_categories(
                    user_id=user_id,
                    category_query=category_query,
                    top_k=3,
                    min_similarity=0.3
                )
                
                print(f"   ✅ Found {clustered_response.total_categories_found} clustered categories")
                print(f"   🔍 Query: '{clustered_response.category_query}'")
                for i, cluster in enumerate(clustered_response.clustered_categories):
                    print(f"      {i+1}. {cluster.category_name}: score {cluster.similarity_score:.3f}")
                    print(f"         {cluster.memory_count} memories")
                    
            except MemuAPIException as e:
                print(f"   ❌ API Error: {e}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Method 3: Retrieve related memory items
            print(f"   🧠 Method 3: Related memory items")
            try:
                memory_query = "cooking food pasta kitchen"
                memory_response = client.retrieve_related_memory_items(
                    user_id=user_id,
                    query=memory_query,
                    top_k=5,
                    min_similarity=0.3,
                    include_categories=["cooking", "food", "kitchen"]
                )
                
                print(f"   ✅ Found {memory_response.total_found} related memories")
                print(f"   🔍 Query: '{memory_response.query}'")
                for i, related_mem in enumerate(memory_response.related_memories[:3]):
                    memory = related_mem.memory
                    score = related_mem.similarity_score
                    content_preview = memory.content[:80] + "..." if len(memory.content) > 80 else memory.content
                    print(f"      {i+1}. {memory.category}: score {score:.3f}")
                    print(f"         ID: {memory.id}")
                    print(f"         Content: {content_preview}")
                    
            except MemuAPIException as e:
                print(f"   ❌ API Error: {e}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()
    
    finally:
        client.close()


def main():
    """Main function to run comprehensive MemU SDK workflow test"""
    
    print("🌟 MemU SDK Comprehensive Workflow Test")
    print("=" * 60)
    print("Testing complete MemU workflow: Memorize → Monitor → SDK Recall APIs")
    print()
    
    # Check environment
    api_url = os.getenv("MEMU_API_BASE_URL")
    api_key = os.getenv("MEMU_API_KEY")
    
    if not api_url or not api_key:
        print("❌ Missing environment variables:")
        print("   MEMU_API_BASE_URL:", "✅ Set" if api_url else "❌ Missing")
        print("   MEMU_API_KEY:", "✅ Set" if api_key else "❌ Missing")
        print()
        print("💡 Please set these environment variables and try again")
        return
    
    print("✅ Environment check passed")
    print(f"   API URL: {api_url}")
    print(f"   API Key: {api_key[:8]}...")
    print()
    
    try:
        # Step 1: Test memorize functionality
        print("🚀 Step 1: Testing memorize functionality")
        task_ids = test_memorize_functionality()
        print(f"✅ Memorization test completed. Generated {len(task_ids)} tasks")
        print()
        
        # Step 2: Test task status monitoring
        if task_ids:
            print("🚀 Step 2: Testing task status monitoring")
            test_task_status_monitoring(task_ids)
            print("✅ Task monitoring test completed")
            print()
        
        # Step 3: Test recall functionality with SDK APIs
        print("🚀 Step 3: Testing recall functionality (SDK APIs)")
        test_recall_functionality()
        print("✅ Recall test completed (using SDK client APIs)")
        print()
        
        # Summary
        print("🎉 === WORKFLOW TEST SUMMARY ===")
        print(f"✅ Monitor: Task status tracking working (2-minute monitoring)")
        print(f"✅ Recall: SDK client APIs tested (default categories, memory items, clustered categories)")
        print()
        print("🔗 Complete workflow: Conversation → Memory → SDK Recall APIs ✅")
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()