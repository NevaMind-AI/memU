"""
PersonaLab 新Memory架构使用示例

演示如何使用根据STRUCTURE.md重构的新Memory系统：
- 统一的Memory类设计
- Memory更新Pipeline
- 数据库存储
- Memory管理器
"""

from personalab.memory import (
    Memory, 
    MemoryManager, 
    ConversationMemoryInterface,
    MemoryRepository
)

def main():
    print("=== PersonaLab 新Memory架构示例 ===\n")
    
    # 1. 创建Memory管理器
    print("1. 初始化Memory管理器...")
    memory_manager = MemoryManager(db_path="example_memory.db")
    conversation_interface = ConversationMemoryInterface(memory_manager)
    
    agent_id = "demo_agent_001"
    
    # 2. 基础Memory操作
    print("\n2. 基础Memory操作...")
    
    # 获取或创建Memory
    memory = memory_manager.get_or_create_memory(agent_id)
    print(f"创建Memory: {memory.memory_id}")
    
    # 直接更新画像信息
    success = memory_manager.update_profile(agent_id, "用户是一名25岁的软件工程师，喜欢编程和阅读")
    print(f"更新画像: {'成功' if success else '失败'}")
    
    # 直接添加事件
    events = [
        "用户询问了Python相关问题",
        "用户表示对机器学习很感兴趣",
        "用户分享了自己的项目经验"
    ]
    success = memory_manager.add_events(agent_id, events)
    print(f"添加事件: {'成功' if success else '失败'}")
    
    # 3. 对话驱动的Memory更新
    print("\n3. 对话驱动的Memory更新...")
    
    # 模拟对话
    conversations = [
        {
            "user": "我最近在学习深度学习，有什么好的建议吗？",
            "assistant": "深度学习是个很有趣的领域！建议从基础的神经网络开始学习。"
        },
        {
            "user": "我用的是PyTorch框架，感觉挺好用的",
            "assistant": "PyTorch确实很受欢迎，特别适合研究和快速原型开发。"
        },
        {
            "user": "我在北京工作，平时也会参加一些技术聚会",
            "assistant": "北京的技术氛围确实很棒，多参加聚会能学到很多东西。"
        }
    ]
    
    # 处理每轮对话
    for i, conv in enumerate(conversations, 1):
        print(f"\n--- 处理第{i}轮对话 ---")
        print(f"用户: {conv['user']}")
        print(f"助手: {conv['assistant']}")
        
        # 通过对话更新Memory
        updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
            agent_id,
            [
                {"role": "user", "content": conv['user']},
                {"role": "assistant", "content": conv['assistant']}
            ]
        )
        
        print(f"Pipeline结果 - 画像更新: {pipeline_result.update_result.profile_updated}")
        print(f"Pipeline结果 - 事件添加: {pipeline_result.update_result.events_added}")
    
    # 4. 获取完整的Memory prompt
    print("\n4. 获取Memory prompt...")
    prompt = memory_manager.get_memory_prompt(agent_id)
    print("当前Memory prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    
    # 5. Memory信息查看
    print("\n5. Memory信息...")
    
    memory_info = memory_manager.get_memory_info(agent_id)
    print(f"Memory ID: {memory_info['memory_id']}")
    print(f"创建时间: {memory_info['created_at']}")
    print(f"更新时间: {memory_info['updated_at']}")
    print(f"画像内容长度: {memory_info['profile_content_length']}")
    print(f"事件数量: {memory_info['event_count']}")
    print(f"ToM置信度: {memory_info['confidence_score']}")
    
    # 6. Memory统计
    print("\n6. Memory统计...")
    stats = memory_manager.get_memory_stats(agent_id)
    print(f"总Memory数: {stats['total_memories']}")
    print(f"总事件数: {stats['total_events']}")
    print(f"最后更新: {stats['last_updated']}")
    
    # 7. 导出和导入Memory
    print("\n7. Memory导出/导入...")
    
    # 导出Memory
    exported_data = memory_manager.export_memory(agent_id)
    print(f"导出Memory数据，包含 {len(exported_data)} 个字段")
    
    # 删除当前Memory
    memory_manager.delete_memory(agent_id)
    print("删除当前Memory")
    
    # 重新导入Memory
    success = memory_manager.import_memory(exported_data)
    print(f"重新导入Memory: {'成功' if success else '失败'}")
    
    # 验证导入结果
    restored_prompt = memory_manager.get_memory_prompt(agent_id)
    print(f"恢复后的prompt长度: {len(restored_prompt)}")
    
    # 8. 对话接口使用
    print("\n8. 对话接口使用...")
    
    # 使用简化的对话接口
    context = conversation_interface.get_context_for_response(agent_id)
    print(f"获取对话上下文，长度: {len(context)}")
    
    # 处理新的一轮对话
    new_prompt = conversation_interface.process_conversation_turn(
        agent_id,
        "我想了解一下如何部署机器学习模型",
        "部署ML模型有很多方式，比如使用Flask、FastAPI或者云服务。"
    )
    print(f"处理新对话后的prompt长度: {len(new_prompt)}")
    
    print("\n=== 示例完成 ===")

def demonstration_memory_components():
    """演示Memory组件的独立使用"""
    print("\n=== Memory组件演示 ===\n")
    
    # 1. 创建独立的Memory对象
    print("1. 创建Memory对象...")
    memory = Memory(agent_id="component_demo")
    
    # 2. 操作ProfileMemory组件
    print("\n2. ProfileMemory组件操作...")
    memory.update_profile("用户是AI研究员，专注于NLP领域")
    print(f"画像内容: {memory.get_profile_content()}")
    
    # 追加画像信息
    memory.update_profile("在清华大学工作，发表过多篇论文")
    print(f"更新后画像: {memory.get_profile_content()}")
    
    # 3. 操作EventMemory组件
    print("\n3. EventMemory组件操作...")
    events = [
        "讨论了Transformer架构",
        "分享了最新的研究进展",
        "询问了关于BERT的技术细节"
    ]
    memory.update_events(events)
    print(f"事件列表: {memory.get_event_content()}")
    
    # 4. 生成prompt
    print("\n4. 生成prompt...")
    prompt = memory.to_prompt()
    print(prompt)
    
    # 5. 转换为字典
    print("\n5. 转换为字典...")
    memory_dict = memory.to_dict()
    print(f"字典包含字段: {list(memory_dict.keys())}")
    
    print("\n=== 组件演示完成 ===")

if __name__ == "__main__":
    main()
    demonstration_memory_components() 