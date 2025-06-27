"""
PersonaLab Conversation 简洁使用模板

这是您要求的conversation输入格式示例：
conversation = [
    {'role': 'user', 'content': 'xxxx'},
    {'role': 'assistant', 'content': 'xxxx'},
    ...
]
"""

from personalab.memory import MemoryManager

def process_conversation(conversation, agent_id="default_agent"):
    """
    处理conversation的简洁函数
    
    Args:
        conversation: List[Dict] - 对话列表，格式为 [{'role': 'user/assistant', 'content': 'xxx'}, ...]
        agent_id: str - Agent标识符
        
    Returns:
        dict: 包含处理结果的字典
    """
    
    # 1. 创建Memory管理器
    memory_manager = MemoryManager(
        db_path=f"{agent_id}_memory.db"
    )
    
    # 2. 处理conversation
    updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
        agent_id, conversation
    )
    
    # 3. 返回结果
    return {
        'memory_prompt': updated_memory.to_prompt(),
        'profile_content': updated_memory.get_profile_content(),
        'event_content': updated_memory.get_event_content(),
        'pipeline_result': {
            'profile_updated': pipeline_result.update_result.profile_updated,
            'events_added': pipeline_result.update_result.events_added,
            'confidence_score': pipeline_result.tom_result.confidence_score
        }
    }


# 使用示例
if __name__ == "__main__":
    
    # 您的conversation输入格式 - 这就是您要的格式！
    conversation = [
        {'role': 'user', 'content': '你好，我是王五，来自深圳，是一名UI设计师'},
        {'role': 'assistant', 'content': '你好王五！UI设计师是很有创意的工作，深圳的设计行业很发达'},
        {'role': 'user', 'content': '是的，我主要做移动应用的界面设计，特别关注用户体验'},
        {'role': 'assistant', 'content': '移动应用UI设计确实需要考虑很多用户体验因素，你有什么设计心得吗？'},
        {'role': 'user', 'content': '我觉得简洁性很重要，还有要考虑不同设备的适配'},
        {'role': 'assistant', 'content': '很好的见解！响应式设计和简洁的界面确实是优秀UI的关键'}
    ]
    
    print("🚀 处理conversation:")
    print("=" * 50)
    for i, msg in enumerate(conversation, 1):
        print(f"{i}. {msg['role']}: {msg['content']}")
    
    print("\n" + "=" * 50)
    
    # 处理conversation
    result = process_conversation(conversation, agent_id="ui_designer_agent")
    
    # 显示结果
    print("📊 处理结果:")
    print(f"- 画像是否更新: {result['pipeline_result']['profile_updated']}")
    print(f"- 添加事件数量: {result['pipeline_result']['events_added']}")
    print(f"- 置信度分数: {result['pipeline_result']['confidence_score']}")
    
    print("\n📋 提取的用户画像:")
    print("-" * 30)
    print(result['profile_content'])
    
    print("\n📝 记录的事件:")
    print("-" * 30)
    for i, event in enumerate(result['event_content'], 1):
        print(f"{i}. {event}")
    
    print("\n🤖 生成的Memory Prompt (可直接用于LLM):")
    print("=" * 60)
    print(result['memory_prompt'])
    print("=" * 60)


# 更简洁的使用方式
def quick_process(conversation, agent_id="quick_agent"):
    """最简洁的处理方式 - 一行代码搞定"""
    memory_manager = MemoryManager(
        db_path=f"{agent_id}.db"
    )
    updated_memory, _ = memory_manager.update_memory_with_conversation(agent_id, conversation)
    return updated_memory.to_prompt()


# 超简洁示例
def ultra_simple_example():
    print("\n" + "="*60)
    print("🚀 超简洁使用示例")
    print("="*60)
    
    # 您的conversation
    my_conversation = [
        {'role': 'user', 'content': '我是小明，喜欢游戏开发'},
        {'role': 'assistant', 'content': '游戏开发很有意思！你用什么引擎？'},
        {'role': 'user', 'content': '主要用Unity做手游'},
        {'role': 'assistant', 'content': 'Unity是很强大的游戏引擎！'}
    ]
    
    # 一行代码处理
    prompt = quick_process(my_conversation, "game_dev_agent")
    
    print("输入conversation，输出Memory prompt:")
    print(prompt)


if __name__ == "__main__":
    # 运行主示例
    print("🎯 运行主示例...")
    # main example code here
    
    # 运行超简洁示例
    ultra_simple_example() 