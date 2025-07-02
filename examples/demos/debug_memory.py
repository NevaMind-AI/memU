#!/usr/bin/env python3
"""Debug memory data structures"""

import sys
sys.path.append('.')

from personalab import Persona

class MockLLMClient:
    def chat_completion(self, messages):
        return "Mock response"

def main():
    print("🔍 调试 PersonaLab Memory 数据结构")
    print("=" * 50)
    
    # 创建persona实例
    persona = Persona(
        agent_id="debug_agent",
        llm_client=MockLLMClient(),
        personality="Debug assistant"
    )
    
    # 添加profile信息
    print("\n1. 添加Profile信息:")
    persona.add_memory("I'm a software engineer", user_id="alice", memory_type="profile")
    persona.add_memory("I work at a tech startup", user_id="alice", memory_type="profile")
    persona.add_memory("I enjoy hiking", user_id="alice", memory_type="profile")
    
    # 添加events
    print("2. 进行对话以生成Events:")
    persona.chat("Hello, how are you?", user_id="alice")
    persona.chat("What's the weather like?", user_id="alice")
    persona.chat("Tell me about Python", user_id="alice")
    
    # 结束会话保存对话到events
    session_result = persona.endsession("alice")
    print(f"Session ended: {session_result}")
    
    # 获取memory详细信息
    print("\n3. 检查Memory数据结构:")
    memory = persona.get_memory("alice")
    
    print(f"\nProfile类型: {type(memory['profile'])}")
    print(f"Profile内容: {memory['profile']}")
    print(f"Profile长度: {len(memory['profile'])}")
    
    print(f"\nEvents类型: {type(memory['events'])}")
    print(f"Events内容: {memory['events']}")
    print(f"Events长度: {len(memory['events'])}")
    
    print(f"\nMind类型: {type(memory['mind'])}")
    print(f"Mind内容: {memory['mind']}")
    print(f"Mind长度: {len(memory['mind'])}")
    
    print("\n4. 查看原始Memory对象:")
    alice_memory_obj = persona._get_or_create_memory("alice")
    
    print(f"\n原始Profile方法返回类型: {type(alice_memory_obj.get_profile())}")
    print(f"原始Profile内容: {alice_memory_obj.get_profile()}")
    
    print(f"\n原始Events方法返回类型: {type(alice_memory_obj.get_events())}")
    print(f"原始Events内容: {alice_memory_obj.get_events()}")
    
    print(f"\n原始Mind方法返回类型: {type(alice_memory_obj.get_mind())}")
    print(f"原始Mind内容: {alice_memory_obj.get_mind()}")
    
    print("\n5. 内部存储方式:")
    print(f"Profile内部存储: {alice_memory_obj.get_profile_content()}")
    print(f"Events内部存储: {alice_memory_obj.get_event_content()}")
    print(f"Mind内部存储: {alice_memory_obj.get_mind_content()}")

if __name__ == "__main__":
    main() 