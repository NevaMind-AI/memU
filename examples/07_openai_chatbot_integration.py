#!/usr/bin/env python3
"""
PersonaLab示例07：OpenAI Quick Start Demo
=========================================

最简单的PersonaLab + OpenAI集成示例
从.env文件读取OPENAI_API_KEY

运行前请确保：
1. 安装PersonaLab：pip install -e .
2. 创建.env文件并设置API key：
   - OPENAI_API_KEY="your-openai-key"
3. 运行脚本：python examples/07_openai_chatbot_integration.py
"""

from personalab import Persona

# 默认使用OpenAI（从.env读取API key）
persona = Persona(agent_id="chatbot_assistant")

def chat_with_memories(message: str) -> str:
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