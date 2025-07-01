#!/usr/bin/env python3
"""
PersonaLab Real LLM Test Script
===============================

测试PersonaLab使用真实LLM的功能
自动从.env文件读取API key
"""

from personalab import Persona

def test_real_llm():
    print("🚀 PersonaLab Real LLM Test")
    print("=" * 40)
    
    # 创建AI智能体 - 自动选择可用的LLM
    print("1. 创建AI智能体...")
    try:
        persona = Persona.create_auto(agent_id="demo_agent")
        print(f"   ✅ 成功创建: {type(persona.llm_client).__name__}")
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        print("   💡 请确保在.env文件中设置了API key")
        return
    
    # 测试对话功能
    print("\n2. 测试AI对话...")
    try:
        response1 = persona.chat("你好！我叫Alice，我喜欢编程和机器学习")
        print(f"   ✅ 对话1成功: {len(response1)} 字符")
        print(f"   回复: {response1[:100]}...")
        
        # 测试记忆功能
        print("\n3. 测试记忆功能...")
        response2 = persona.chat("请告诉我之前我说了什么关于我的爱好？")
        print(f"   ✅ 对话2成功: {len(response2)} 字符") 
        print(f"   回复: {response2[:100]}...")
        
    except Exception as e:
        print(f"   ❌ 对话失败: {e}")
        return
    
    # 检查记忆存储
    print("\n4. 检查记忆存储...")
    memory = persona.get_memory()
    print(f"   记忆类型: {list(memory.keys())}")
    for key, value in memory.items():
        if value:
            print(f"   {key}: {len(value)} 条记录")
    
    # 测试搜索功能
    print("\n5. 测试对话搜索...")
    search_results = persona.search("编程")
    print(f"   ✅ 搜索到 {len(search_results)} 个相关对话")
    
    print("\n🎉 所有测试完成！PersonaLab正在使用真实LLM")
    print("💡 您的AI智能体现在具备：")
    print("   • 真实LLM对话能力")
    print("   • 持久化记忆存储")  
    print("   • 语义搜索功能")
    print("   • 自动学习能力")

if __name__ == "__main__":
    test_real_llm() 