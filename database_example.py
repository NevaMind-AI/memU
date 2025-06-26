#!/usr/bin/env python3
"""
Database example for PersonaLab Memory system.
Demonstrates both manual and automatic persistence.
"""

import os
from personalab.memory import Memory
from personalab.database import MemoryDatabase, PersistentMemory

def demo_manual_persistence():
    """Demonstrate manual database save/load."""
    print("Manual Persistence Demo")
    print("=" * 30)
    
    # Clean up any existing database
    db_path = "manual_demo.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create database and memory
    db = MemoryDatabase(db_path)
    memory = Memory("chatbot_demo")
    
    # Setup agent
    agent = memory.get_agent_memory()
    agent.profile.set_profile("ChatBot Demo v1.0, Supports Chinese and English")
    agent.events.add_memory("系统初始化")
    agent.events.add_memory("加载语言模型")
    agent.events.add_memory("准备接收用户请求")
    
    # Setup some users
    alice = memory.get_user_memory("alice")
    alice.profile.set_profile("Name: Alice, Language: Chinese, Interests: Technology, AI")
    alice.events.add_memory("用户首次连接")
    alice.events.add_memory("询问AI的能力")
    alice.events.add_memory("对AI回答很满意")
    
    bob = memory.get_user_memory("bob")
    bob.profile.set_profile("Name: Bob, Language: English, Interests: Programming, Science")
    bob.events.add_memory("User connected for the first time")
    bob.events.add_memory("Asked about programming help")
    bob.events.add_memory("Received detailed code examples")
    
    print(f"Created memory with {len(memory.list_users())} users")
    print(f"Agent events: {agent.events.get_size()}")
    print(f"Alice events: {alice.events.get_size()}")
    print(f"Bob events: {bob.events.get_size()}")
    
    # Manual save
    print("\n🔄 Saving to database...")
    db.save_memory(memory)
    
    # Simulate program restart - load from database
    print("🔄 Simulating program restart...")
    loaded_memory = db.load_memory("chatbot_demo")
    
    # Verify data
    print("✅ Data loaded successfully!")
    loaded_agent = loaded_memory.get_agent_memory()
    loaded_alice = loaded_memory.get_user_memory("alice")
    loaded_bob = loaded_memory.get_user_memory("bob")
    
    print(f"Agent profile: {loaded_agent.profile.get_profile()}")
    print(f"Alice latest memory: {loaded_alice.events.get_recent_memories(1)[0]}")
    print(f"Bob latest memory: {loaded_bob.events.get_recent_memories(1)[0]}")
    
    # Show database stats
    stats = db.get_stats()
    print(f"\nDatabase contains {stats['agents']} agents, {stats['users']} users, {stats['events']} events")
    
    # Cleanup
    os.remove(db_path)
    print(f"Demo completed, cleaned up {db_path}\n")

def demo_auto_persistence():
    """Demonstrate automatic persistence."""
    print("Auto-Persistence Demo")
    print("=" * 25)
    
    # Clean up any existing database
    db_path = "auto_demo.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create persistent memory with auto-save
    print("Creating PersistentMemory with auto-save...")
    memory = PersistentMemory("smart_assistant", db_path, auto_save=True)
    
    # Setup agent (auto-saves)
    agent = memory.get_agent_memory()
    agent.profile.set_profile("Smart Assistant v2.0, Multi-language, Context-aware")
    agent.events.add_memory("Advanced system started")
    print("✅ Agent data added (auto-saved)")
    
    # Add user data (auto-saves automatically)
    alice = memory.get_user_memory("alice")
    alice.profile.set_profile("Alice: Tech enthusiast, prefers detailed explanations")
    alice.events.add_memory("Alice joined the conversation")
    alice.events.add_memory("Asked about latest AI developments")
    print("✅ Alice data added (auto-saved)")
    
    # Add another user
    charlie = memory.get_user_memory("charlie")
    charlie.profile.set_profile("Charlie: Student, needs simple explanations")
    charlie.events.add_memory("Charlie started learning session")
    charlie.events.add_memory("Asked basic questions about programming")
    print("✅ Charlie data added (auto-saved)")
    
    # Show current state
    print(f"\nCurrent state: {len(memory.list_users())} users")
    
    # Simulate program restart - create new instance
    print("\n🔄 Simulating program restart...")
    memory2 = PersistentMemory("smart_assistant", db_path, auto_save=False)
    
    # Data should be automatically loaded
    agent2 = memory2.get_agent_memory()
    alice2 = memory2.get_user_memory("alice")
    charlie2 = memory2.get_user_memory("charlie")
    
    print("✅ Data automatically restored!")
    print(f"Agent: {agent2.profile.get_profile()[:50]}...")
    print(f"Alice events: {alice2.events.get_size()}")
    print(f"Charlie events: {charlie2.events.get_size()}")
    
    # Add more data to loaded instance (without auto-save)
    charlie2.events.add_memory("Continued learning Python basics")
    
    # Manual save since auto_save=False for this instance
    memory2.save()
    print("✅ Manually saved additional data")
    
    # Show final stats
    stats = memory2.db.get_stats()
    print(f"\nFinal database: {stats['events']} total events")
    
    # Cleanup
    os.remove(db_path)
    print(f"Demo completed, cleaned up {db_path}\n")

def demo_database_management():
    """Demonstrate database management features."""
    print("Database Management Demo")
    print("=" * 28)
    
    db_path = "management_demo.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = MemoryDatabase(db_path)
    
    # Create multiple agents
    agents = ["chatbot_v1", "assistant_v2", "helper_v3"]
    for agent_id in agents:
        memory = Memory(agent_id)
        
        # Agent setup
        agent = memory.get_agent_memory()
        agent.profile.set_profile(f"Agent {agent_id} profile")
        agent.events.add_memory(f"{agent_id} initialized")
        
        # Add users
        for user_id in ["user_1", "user_2"]:
            user = memory.get_user_memory(user_id)
            user.profile.set_profile(f"User {user_id} for {agent_id}")
            user.events.add_memory(f"{user_id} connected to {agent_id}")
        
        db.save_memory(memory)
    
    print(f"Created {len(agents)} agents with 2 users each")
    
    # List all agents
    all_agents = db.list_agents()
    print(f"Agents in database: {all_agents}")
    
    # List users for specific agent
    users = db.list_users("chatbot_v1")
    print(f"Users for chatbot_v1: {users}")
    
    # Delete a specific user
    deleted = db.delete_user("chatbot_v1", "user_1")
    print(f"Deleted user_1 from chatbot_v1: {deleted}")
    
    # Check remaining users
    users = db.list_users("chatbot_v1")
    print(f"Remaining users for chatbot_v1: {users}")
    
    # Delete entire agent
    deleted = db.delete_agent("helper_v3")
    print(f"Deleted helper_v3 agent: {deleted}")
    
    # Final stats
    stats = db.get_stats()
    print(f"\nFinal stats:")
    print(f"  Agents: {stats['agents']}")
    print(f"  Users: {stats['users']}")
    print(f"  Events: {stats['events']}")
    print(f"  Database size: {stats['database_size_bytes']} bytes")
    
    # Cleanup
    os.remove(db_path)
    print(f"Demo completed, cleaned up {db_path}")

def main():
    """Run all database demos."""
    print("PersonaLab Database Demo")
    print("=" * 40)
    print("Demonstrating SQLite persistence for Memory system\n")
    
    demo_manual_persistence()
    demo_auto_persistence()
    demo_database_management()
    
    print("=" * 40)
    print("🎉 All database demos completed!")
    print("✅ Manual save/load: Full control over persistence")
    print("✅ Auto-save: Automatic persistence on data changes")
    print("✅ Management: Create, read, update, delete operations")
    print("✅ SQLite: Lightweight, file-based, no server required")
    print("✅ Data integrity: All Memory data preserved perfectly")

if __name__ == "__main__":
    main() 