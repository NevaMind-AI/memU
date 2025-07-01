#!/usr/bin/env python3
"""
PersonaLab示例07：OpenAI Quick Start Demo
=======================================

最简单的PersonaLab + OpenAI集成示例

运行前请确保：
1. 安装PersonaLab：pip install -e .
2. 安装OpenAI：pip install openai>=1.0.0
3. 设置环境变量：export OPENAI_API_KEY="your-api-key"
"""

from personalab import Persona

persona = Persona.create_mock(agent_id="default_agent")

def chat_with_memories(message: str, agent_id: str = "default_agent") -> str:
    return persona.chat(message)

def main():
    print("🚀 PersonaLab Quick Start Demo")
    print("Chat with AI (type 'exit' to quit)")
    print("-" * 40)
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        
        try:
            response = chat_with_memories(user_input)
            print(f"AI: {response}")
        except Exception as e:
            print(f"Error: {e}")
            print("Make sure you have set OPENAI_API_KEY environment variable")

if __name__ == "__main__":
    main() 