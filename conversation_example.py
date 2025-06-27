"""
PersonaLab Conversation处理示例

演示如何使用conversation输入来更新Memory系统
"""

from personalab.memory import MemoryManager, ConversationMemoryInterface
import json

def main():
    print("=== PersonaLab Conversation处理示例 ===\n")
    
    # 1. 初始化Memory管理器（默认使用LLM）
    print("1. 初始化Memory管理器（使用LLM驱动）...")
    memory_manager = MemoryManager(
        db_path="conversation_example.db"
    )
    conversation_interface = ConversationMemoryInterface(memory_manager)
    
    agent_id = "assistant_001"
    
    # 2. 示例conversation - 这是您想要的输入格式
    print("\n2. 准备conversation数据...")
    
    # 第一段对话 - 用户介绍自己
    conversation_1 = [
        {
            'role': 'user', 
            'content': '你好！我是张三，今年25岁，是一名软件工程师。我喜欢编程，特别是Python和机器学习。'
        },
        {
            'role': 'assistant', 
            'content': '你好张三！很高兴认识你。作为软件工程师，你一定有很丰富的编程经验。Python和机器学习是很好的技能组合！'
        },
        {
            'role': 'user', 
            'content': '是的，我在北京工作，主要做数据分析和AI模型开发。最近在学习深度学习框架PyTorch。'
        },
        {
            'role': 'assistant', 
            'content': 'PyTorch是个很棒的深度学习框架！在北京的AI行业发展机会很多。你在数据分析和AI模型开发方面有什么具体的项目经验吗？'
        }
    ]
    
    # 第二段对话 - 技术讨论
    conversation_2 = [
        {
            'role': 'user', 
            'content': '我最近在做一个推荐系统项目，使用协同过滤和深度学习的混合方法。'
        },
        {
            'role': 'assistant', 
            'content': '推荐系统很有意思！协同过滤和深度学习结合能够很好地平衡效果和可解释性。你们的数据规模大概有多大？'
        },
        {
            'role': 'user', 
            'content': '大概有100万用户，1000万的交互记录。我们使用了embedding技术来处理稀疏性问题。'
        },
        {
            'role': 'assistant', 
            'content': '这个规模已经不小了！embedding确实是处理稀疏性的好方法。你们有考虑冷启动问题的解决方案吗？'
        }
    ]
    
    # 第三段对话 - 个人兴趣
    conversation_3 = [
        {
            'role': 'user', 
            'content': '除了工作，我平时喜欢打篮球，周末经常和朋友一起打球。还喜欢看技术博客和参加技术meetup。'
        },
        {
            'role': 'assistant', 
            'content': '很好的爱好！运动能帮助保持身心健康，而参加技术meetup是很好的学习和交流方式。你有关注哪些技术博客吗？'
        },
        {
            'role': 'user', 
            'content': '我经常看机器之心、AI科技大本营，还有一些国外的像Towards Data Science。'
        },
        {
            'role': 'assistant', 
            'content': '这些都是很优质的技术资源！机器之心的文章质量很高，Towards Data Science上也有很多实用的教程和案例分析。'
        }
    ]
    
    print("准备了3段conversation，总共12条消息")
    
    # 3. 处理第一段对话
    print("\n3. 处理第一段对话（用户介绍）...")
    print("=" * 50)
    for msg in conversation_1:
        print(f"{msg['role']}: {msg['content'][:50]}...")
    
    updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
        agent_id, conversation_1
    )
    
    print(f"\nPipeline结果:")
    print(f"- 画像更新: {pipeline_result.update_result.profile_updated}")
    print(f"- 事件添加: {pipeline_result.update_result.events_added}")
    print(f"- ToM置信度: {pipeline_result.tom_result.confidence_score}")
    
    # 4. 查看第一次更新后的Memory
    print(f"\n4. 第一次更新后的Memory状态...")
    memory_summary = memory_manager.get_memory_info(agent_id)
    print(f"- 画像长度: {memory_summary['profile_content_length']}")
    print(f"- 事件数量: {memory_summary['event_count']}")
    
    current_prompt = memory_manager.get_memory_prompt(agent_id)
    print(f"\n当前Memory Prompt:")
    print("-" * 40)
    print(current_prompt)
    print("-" * 40)
    
    # 5. 处理第二段对话
    print("\n5. 处理第二段对话（技术讨论）...")
    print("=" * 50)
    for msg in conversation_2:
        print(f"{msg['role']}: {msg['content'][:50]}...")
    
    updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
        agent_id, conversation_2
    )
    
    print(f"\nPipeline结果:")
    print(f"- 画像更新: {pipeline_result.update_result.profile_updated}")
    print(f"- 事件添加: {pipeline_result.update_result.events_added}")
    
    # 6. 处理第三段对话
    print("\n6. 处理第三段对话（个人兴趣）...")
    print("=" * 50)
    for msg in conversation_3:
        print(f"{msg['role']}: {msg['content'][:50]}...")
    
    updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
        agent_id, conversation_3
    )
    
    print(f"\nPipeline结果:")
    print(f"- 画像更新: {pipeline_result.update_result.profile_updated}")
    print(f"- 事件添加: {pipeline_result.update_result.events_added}")
    
    # 7. 查看最终的Memory状态
    print(f"\n7. 最终Memory状态...")
    final_memory_info = memory_manager.get_memory_info(agent_id)
    print(f"Memory信息:")
    print(f"- Memory ID: {final_memory_info['memory_id']}")
    print(f"- 画像长度: {final_memory_info['profile_content_length']}")
    print(f"- 事件数量: {final_memory_info['event_count']}")
    print(f"- 最后更新: {final_memory_info['updated_at']}")
    
    # 8. 展示最终的Memory内容
    print(f"\n8. 最终Memory内容...")
    final_memory = memory_manager.get_or_create_memory(agent_id)
    
    print("\n📋 用户画像:")
    print("-" * 40)
    print(final_memory.get_profile_content())
    
    print("\n📝 事件记录:")
    print("-" * 40)
    events = final_memory.get_event_content()
    for i, event in enumerate(events, 1):
        print(f"{i}. {event}")
    
    print(f"\n🧠 Theory of Mind分析:")
    print("-" * 40)
    if final_memory.tom_metadata:
        insights = final_memory.tom_metadata.get('insights', {})
        print(f"- 主要意图: {insights.get('intent_analysis', {}).get('primary_intent', 'unknown')}")
        print(f"- 主导情绪: {insights.get('emotion_analysis', {}).get('dominant_emotion', 'unknown')}")
        print(f"- 参与度: {insights.get('behavior_patterns', {}).get('engagement_level', 'unknown')}")
        print(f"- 置信度: {final_memory.tom_metadata.get('confidence_score', 0)}")
    
    # 9. 展示完整的prompt格式
    print(f"\n9. 完整Memory Prompt (用于LLM)...")
    print("=" * 60)
    final_prompt = final_memory.to_prompt()
    print(final_prompt)
    print("=" * 60)
    
    # 10. 演示Memory导出
    print(f"\n10. Memory数据导出...")
    exported_data = memory_manager.export_memory(agent_id)
    print(f"导出数据包含字段: {list(exported_data.keys())}")
    
    # 保存为JSON文件
    with open('exported_memory.json', 'w', encoding='utf-8') as f:
        json.dump(exported_data, f, ensure_ascii=False, indent=2)
    print("Memory数据已导出到 exported_memory.json")
    
    print("\n=== 示例完成 ===")
    print("\n💡 使用要点:")
    print("1. conversation是包含role和content的字典列表")
    print("2. role可以是'user'或'assistant'")
    print("3. Memory会自动分析并更新画像和事件")
    print("4. Pipeline提供详细的处理结果")
    print("5. Memory支持导出/导入，便于数据管理")


def simple_example():
    """简化版本的使用示例"""
    print("\n=== 简化版本示例 ===\n")
    
    # 你的conversation输入格式
    conversation = [
        {'role': 'user', 'content': '我是李四，今年30岁，在上海做产品经理'},
        {'role': 'assistant', 'content': '你好李四！产品经理是很有挑战性的工作'},
        {'role': 'user', 'content': '是的，我主要负责移动端产品的设计和规划'},
        {'role': 'assistant', 'content': '移动端产品设计需要很强的用户体验意识'}
    ]
    
    # 创建Memory管理器（使用LLM）
    memory_manager = MemoryManager(
        db_path="simple_example.db"
    )
    agent_id = "simple_agent"
    
    # 处理conversation
    print("输入conversation:")
    for msg in conversation:
        print(f"  {msg['role']}: {msg['content']}")
    
    # 更新Memory
    updated_memory, result = memory_manager.update_memory_with_conversation(
        agent_id, conversation
    )
    
    # 查看结果
    print(f"\n处理结果:")
    print(f"- 画像更新: {result.update_result.profile_updated}")
    print(f"- 事件添加: {result.update_result.events_added}")
    
    # 获取Memory prompt
    prompt = memory_manager.get_memory_prompt(agent_id)
    print(f"\n生成的Memory Prompt:")
    print(prompt)


if __name__ == "__main__":
    # 运行完整示例
    main()
    
    # 运行简化示例
    simple_example() 