#!/usr/bin/env python3
"""
PersonaLab Default OpenAI Test
==============================

测试PersonaLab默认使用OpenAI的简化API
从.env文件自动读取OPENAI_API_KEY
"""

from personalab import Persona

def test_default_openai():
    print("🚀 PersonaLab Default OpenAI Test")
    print("=" * 40)
    
    # 最简单的用法 - 默认使用OpenAI
    print("1. 创建AI智能体（默认OpenAI）...")
    try:
        persona = Persona(agent_id="demo_assistant")
        print(f"   ✅ 成功创建: {type(persona.llm_client).__name__}")
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        print("   💡 请确保在.env文件中设置了OPENAI_API_KEY")
        return
    
    # 测试基本对话
    print("\n2. 测试基本对话...")
    try:
        response1 = persona.chat("你好！我是PersonaLab的用户")
        print(f"   ✅ 对话成功: {len(response1)} 字符")
        print(f"   回复: {response1[:80]}...")
        
    except Exception as e:
        print(f"   ❌ 对话失败: {e}")
        return
    
    # 测试记忆功能
    print("\n3. 测试记忆功能...")
    try:
        response2 = persona.chat("我喜欢机器学习和深度学习")
        print(f"   ✅ 记忆存储成功")
        
        response3 = persona.chat("我刚才说了什么兴趣爱好？")
        print(f"   ✅ 记忆检索成功: {len(response3)} 字符")
        print(f"   回复: {response3[:80]}...")
        
    except Exception as e:
        print(f"   ❌ 记忆测试失败: {e}")
        return
    
    # 检查存储的记忆
    print("\n4. 检查存储的记忆...")
    memory = persona.get_memory()
    print(f"   记忆类型: {list(memory.keys())}")
    
    # 测试搜索功能
    print("\n5. 测试对话搜索...")
    search_results = persona.search("机器学习")
    print(f"   ✅ 搜索到 {len(search_results)} 个相关对话")
    
    print("\n🎉 所有测试完成！")
    print("💡 PersonaLab现在默认使用OpenAI，API更加简洁：")
    print("   • 一行代码创建AI智能体")
    print("   • 自动从.env读取API key")
    print("   • 无需复杂配置")
    print("   • 开箱即用的记忆功能")

if __name__ == "__main__":
    test_default_openai() 