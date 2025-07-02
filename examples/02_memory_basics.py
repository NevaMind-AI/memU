#!/usr/bin/env python3
"""
02_memory_basics.py

PersonaLab多用户记忆管理示例

演示如何：
1. 一个Persona实例为多个用户服务
2. 不同用户的记忆隔离
3. 多种记忆类型管理 (profile, event, mind)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab import Persona

def main():
    print("=== PersonaLab 记忆管理示例 ===\n")
    
    # 为了演示，使用mock LLM函数
    def mock_llm_function(messages, **kwargs):
        user_msg = messages[-1]["content"] if messages else ""
        return f"Mock LLM response to: '{user_msg}'"
    
    from personalab.llm import CustomLLMClient
    custom_client = CustomLLMClient(llm_function=mock_llm_function)
    
    # 1. 创建Persona实例
    persona = Persona(
        agent_id="memory_assistant",
        llm_client=custom_client,
        personality="You are a helpful AI assistant that remembers user preferences."
    )
    
    print("1. 为不同用户创建记忆...")
    
    # 为用户1添加记忆
    print("\n👤 用户1的对话:")
    persona.add_memory("喜欢喝咖啡", "profile", "user1")
    persona.add_memory("是程序员", "profile", "user1")
    response1 = persona.chat("你好", user_id="user1")
    print(f"用户1: 你好")
    print(f"AI: {response1}")
    
    # 为用户2添加记忆
    print("\n👤 用户2的对话:")
    persona.add_memory("喜欢喝茶", "profile", "user2")
    persona.add_memory("是设计师", "profile", "user2")
    response2 = persona.chat("你好", user_id="user2")
    print(f"用户2: 你好")
    print(f"AI: {response2}")
    
    print("\n2. 验证不同用户的记忆隔离...")
    user1_memory = persona.get_memory("user1")
    user2_memory = persona.get_memory("user2")
    
    print(f"用户1的记忆: {user1_memory}")
    print(f"用户2的记忆: {user2_memory}")
    
    print("\n3. 测试事件记忆...")
    persona.add_memory("学习了Python", "event", "user1")
    persona.add_memory("设计了一个logo", "event", "user2")
    
    print(f"用户1事件: {persona.get_memory('user1')['events']}")
    print(f"用户2事件: {persona.get_memory('user2')['events']}")
    
    print("\n4. 测试心理洞察...")
    persona.add_memory("对技术很感兴趣", "mind", "user1")
    persona.add_memory("注重视觉美感", "mind", "user2")
    
    print(f"用户1洞察: {persona.get_memory('user1')['mind']}")
    print(f"用户2洞察: {persona.get_memory('user2')['mind']}")
    
    print("\n5. 多轮对话测试...")
    print("\n👤 用户1继续对话:")
    resp1_1 = persona.chat("我在学习Python编程", user_id="user1")
    print(f"用户1: 我在学习Python编程")
    print(f"AI: {resp1_1}")
    
    print("\n👤 用户2继续对话:")
    resp2_1 = persona.chat("我在做UI设计", user_id="user2")
    print(f"用户2: 我在做UI设计")
    print(f"AI: {resp2_1}")
    
    print("\n6. 结束会话...")
    result1 = persona.endsession("user1")
    result2 = persona.endsession("user2")
    print(f"用户1会话结果: {result1}")
    print(f"用户2会话结果: {result2}")
    
    # 清理资源
    persona.close()
    
    print("\n=== 示例完成 ===")
    print("\n💡 学到的知识点:")
    print("1. ✅ 如何为多个用户管理独立的记忆")
    print("2. ✅ 不同类型的记忆管理 (profile, event, mind)")
    print("3. ✅ 用户间的记忆隔离")
    print("4. ✅ 多用户对话管理")


if __name__ == "__main__":
    main() 