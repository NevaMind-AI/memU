#!/usr/bin/env python3
"""示例：显示完整的Events内容"""

import sys
sys.path.append('.')

from personalab import Persona

class MockLLMClient:
    def chat_completion(self, messages):
        return "Mock response"

def main():
    persona = Persona(
        agent_id="demo_agent",
        llm_client=MockLLMClient(),
        personality="Demo assistant"
    )
    
    # 添加一些对话
    persona.chat("Hello", user_id="alice")
    persona.chat("How are you?", user_id="alice")
    persona.endsession("alice")
    
    # 获取memory
    memory = persona.get_memory("alice")
    
    print("🔍 Events 数据结构:")
    print(f"类型: {type(memory['events'])}")
    print(f"长度: {len(memory['events'])}")
    print(f"内容:")
    for i, event in enumerate(memory['events'], 1):
        print(f"  {i}. {event}")

if __name__ == "__main__":
    main() 