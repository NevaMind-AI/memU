#!/usr/bin/env python3
"""
🎯 PersonaLab 简化架构最终验证

验证移除传统pipeline后，系统是否正常工作
"""

from personalab.memory import MemoryManager
from personalab.memory import create_llm_client

def test_simplified_architecture():
    """测试简化后的架构"""
    print("🔬 PersonaLab 简化架构验证")
    print("=" * 50)
    
    # 1. 测试默认创建
    print("\n1️⃣ 测试默认创建...")
    manager = MemoryManager()
    print("✅ MemoryManager() 创建成功")
    
    # 2. 测试基本功能
    print("\n2️⃣ 测试基本Memory功能...")
    conversation = [
        {'role': 'user', 'content': '我是测试用户，做Python开发'},
        {'role': 'assistant', 'content': '很高兴认识你！Python是很棒的语言'}
    ]
    
    agent_id = "test_user"
    memory, result = manager.update_memory_with_conversation(agent_id, conversation)
    
    print(f"✅ 对话处理成功")
    print(f"   - 画像更新: {result.update_result.profile_updated}")
    print(f"   - 事件添加: {result.update_result.events_added}")
    print(f"   - ToM置信度: {result.tom_result.confidence_score}")
    
    # 3. 测试Memory输出
    print("\n3️⃣ 测试Memory输出...")
    prompt = memory.to_prompt()
    print("✅ Memory prompt生成成功")
    print(f"   - 长度: {len(prompt)} 字符")
    
    # 4. 测试自定义LLM客户端
    print("\n4️⃣ 测试自定义LLM客户端...")
    mock_client = create_llm_client("mock")
    custom_manager = MemoryManager(llm_client=mock_client, temperature=0.5)
    print("✅ 自定义LLM客户端创建成功")
    
    # 5. 测试数据持久化
    print("\n5️⃣ 测试数据持久化...")
    memory_info = manager.get_memory_info(agent_id)
    print("✅ Memory信息获取成功")
    print(f"   - Agent ID: {memory_info['agent_id']}")
    print(f"   - 画像长度: {memory_info['profile_content_length']}")
    print(f"   - 事件数量: {memory_info['event_count']}")
    
    print("\n🎉 所有测试通过！PersonaLab简化架构工作正常")

if __name__ == "__main__":
    test_simplified_architecture() 