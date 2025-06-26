#!/usr/bin/env python3
"""
Simple example of the PersonaLab memory system:
Memory (container)
├── UserMemory (profile + events)  
└── AgentMemory (profile + events)
"""

from personalab.memory import Memory

def main():
    print("PersonaLab - New Memory Architecture Example")
    print("=" * 50)
    
    # Create the main Memory container
    print("1. Create Memory Container")
    print("-" * 25)
    
    memory = Memory("chatbot_v1")
    print(f"Created: {memory}")
    print()
    
    # Agent Memory (profile + events)
    print("2. Agent Memory")
    print("-" * 15)
    
    agent = memory.get_agent_memory()
    print(f"Agent memory: {agent}")
    
    # Agent profile (string)
    agent.profile.set_profile("System: ChatBot v1.0, Language: Chinese, Status: Active, Capabilities: Weather, Q&A")
    print(f"Agent profile: {agent.profile.get_profile()}")
    
    # Agent events (list of strings)
    agent.events.add_memory("系统启动")
    agent.events.add_memory("模型加载完成")
    agent.events.add_memory("准备服务用户")
    
    print(f"Agent events count: {agent.events.get_size()}")
    print("Agent recent events:")
    for event in agent.events.get_recent_memories(2):
        print(f"  {event}")
    print()
    
    # User Memory (profile + events)
    print("3. User Memories")
    print("-" * 16)
    
    # User Alice
    alice = memory.get_user_memory("alice")
    print(f"Alice memory: {alice}")
    
    alice.profile.set_profile("Name: Alice, Age: 25, Language: Chinese, Skill: Beginner, Interests: Weather, Daily Life")
    alice.events.add_memory("用户连接")
    alice.events.add_memory("询问今天天气")
    alice.events.add_memory("获得天气信息")
    alice.events.add_memory("表示感谢")
    
    print(f"Alice profile: {alice.profile.get_profile()}")
    print(f"Alice events: {alice.events.get_size()}")
    
    # User Bob
    bob = memory.get_user_memory("bob")
    print(f"Bob memory: {bob}")
    
    bob.profile.set_profile("Name: Bob, Age: 30, Language: English, Skill: Advanced, Interests: AI, Technology")
    bob.events.add_memory("User connected")
    bob.events.add_memory("Asked about AI capabilities")
    bob.events.add_memory("Discussed machine learning")
    bob.events.add_memory("Requested code examples")
    
    print(f"Bob profile: {bob.profile.get_profile()}")
    print(f"Bob events: {bob.events.get_size()}")
    print()
    
    # Memory operations
    print("4. Memory Operations")
    print("-" * 20)
    
    # Search Alice's memories
    alice_weather = alice.events.search_memories("天气")
    print(f"Alice's weather-related memories: {len(alice_weather)}")
    for mem in alice_weather:
        print(f"  {mem}")
    
    # Search Bob's memories
    bob_ai = bob.events.search_memories("AI")
    print(f"Bob's AI-related memories: {len(bob_ai)}")
    for mem in bob_ai:
        print(f"  {mem}")
    print()
    
    # Memory summary
    print("5. Memory Summary")
    print("-" * 17)
    
    info = memory.get_memory_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print(f"Registered users: {memory.list_users()}")
    print()
    
    # Architecture summary
    print("6. Architecture Summary")
    print("-" * 22)
    print("✅ Memory: Main container for agent memories")
    print("✅ AgentMemory: Contains agent profile + events")
    print("✅ UserMemory: Contains user profile + events")
    print("✅ ProfileMemory: Simple string storage")
    print("✅ EventMemory: Simple list with timestamps")
    print("✅ Clean separation between agent and users")
    print("✅ Easy-to-use hierarchical API")
    
    print("\n🎉 New architecture is clean and powerful!")

if __name__ == "__main__":
    main() 