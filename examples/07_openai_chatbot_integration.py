#!/usr/bin/env python3
"""
PersonaLab示例07：LLM Quick Start Demo
=====================================

最简单的PersonaLab + LLM集成示例
自动从.env文件读取API key，支持多种LLM提供商

运行前请确保：
1. 安装PersonaLab：pip install -e .
2. 创建.env文件并设置API key：
   - OPENAI_API_KEY="your-openai-key"
   - 或 ANTHROPIC_API_KEY="your-anthropic-key"
3. 运行脚本：python examples/07_openai_chatbot_integration.py
"""

from personalab import Persona

# 自动选择可用的LLM（推荐方式）
persona = Persona.create_auto(agent_id="chatbot_assistant")

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