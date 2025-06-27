"""
PersonaLab LLM驱动的Memory更新示例

展示如何使用LLM客户端进行智能的Memory分析和更新
"""

from personalab.memory import (
    MemoryManager, 
    create_llm_client,
    OpenAIClient
)

def create_basic_memory_manager(**llm_config):
    """
    创建基础Memory管理器（不依赖外部LLM API）
    
    Args:
        **llm_config: LLM配置参数
    """
    # 创建不依赖外部API的Memory管理器
    memory_manager = MemoryManager(
        db_path="basic_memory.db",
        llm_client=None,  # 使用基础fallback功能
        **llm_config
    )
    
    return memory_manager

def create_openai_memory_manager(api_key, **llm_config):
    """
    创建OpenAI驱动的Memory管理器
    
    Args:
        api_key: OpenAI API密钥
        **llm_config: LLM配置参数
    """
    # 创建OpenAI客户端
    llm_client = create_llm_client("openai", api_key=api_key)
    
    # 创建使用OpenAI的MemoryManager
    memory_manager = MemoryManager(
        db_path="openai_memory.db",
        llm_client=llm_client,
        temperature=0.3,
        max_tokens=2000,
        **llm_config
    )
    
    return memory_manager


def basic_conversation_example():
    """基础conversation处理示例（使用fallback功能）"""
    print("🤖 基础Memory更新示例")
    print("=" * 60)
    
    # 创建基础Memory管理器
    memory_manager = create_basic_memory_manager()
    
    agent_id = "basic_agent_001"
    
    # 示例conversation
    conversation = [
        {
            'role': 'user', 
            'content': '你好！我是李明，今年28岁，在上海做前端开发工程师。我特别喜欢React和Vue.js框架。'
        },
        {
            'role': 'assistant', 
            'content': '你好李明！前端开发是很有趣的工作，React和Vue都是很流行的框架。你在上海的哪个区域工作呢？'
        },
        {
            'role': 'user', 
            'content': '我在浦东新区的一家互联网公司工作，主要做电商平台的前端开发。最近在学习TypeScript和Next.js。'
        },
        {
            'role': 'assistant', 
            'content': 'TypeScript确实是前端开发的趋势，Next.js也是React生态中很强大的框架。电商平台对用户体验要求很高吧？'
        },
        {
            'role': 'user', 
            'content': '是的，我们特别注重性能优化和用户体验。除了工作，我还喜欢参加技术meetup，经常在掘金和GitHub上分享代码。'
        },
        {
            'role': 'assistant', 
            'content': '很棒！技术分享是很好的学习方式。你在GitHub上有什么比较有趣的项目吗？'
        }
    ]
    
    print("📝 输入conversation:")
    print("-" * 40)
    for i, msg in enumerate(conversation, 1):
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        print(f"{i}. {role_emoji} {msg['role']}: {msg['content'][:50]}...")
    
    print(f"\n🔄 使用基础Pipeline处理conversation...")
    
    # 使用基础pipeline处理conversation
    updated_memory, result = memory_manager.update_memory_with_conversation(
        agent_id, conversation
    )
    
    print(f"\n✅ 基础处理完成！")
    print("-" * 40)
    
    # 显示pipeline结果
    print(f"📊 Pipeline结果:")
    print(f"- 画像更新: {result.update_result.profile_updated}")
    print(f"- 事件添加: {result.update_result.events_added}")
    print(f"- 分析置信度: {result.modification_result.analysis_confidence:.2f}")
    print(f"- ToM置信度: {result.tom_result.confidence_score:.2f}")
    
    # 显示提取的信息
    print(f"\n🧠 提取的画像更新:")
    print("-" * 30)
    for i, update in enumerate(result.modification_result.profile_updates, 1):
        print(f"{i}. {update}")
    
    print(f"\n📝 提取的事件:")
    print("-" * 30)
    for i, event in enumerate(result.modification_result.events, 1):
        print(f"{i}. {event}")
    
    # 显示更新后的画像
    print(f"\n👤 更新后的用户画像:")
    print("-" * 40)
    print(updated_memory.get_profile_content())
    
    # 显示Theory of Mind分析
    print(f"\n🧠 Theory of Mind分析:")
    print("-" * 40)
    tom_insights = result.tom_result.insights
    
    if 'intent_analysis' in tom_insights:
        intent = tom_insights['intent_analysis']
        print(f"💭 意图分析: {intent.get('primary_intent', 'unknown')}")
    
    if 'emotion_analysis' in tom_insights:
        emotion = tom_insights['emotion_analysis']
        print(f"😊 情绪分析: {emotion.get('dominant_emotion', 'unknown')}")
    
    if 'behavior_patterns' in tom_insights:
        behavior = tom_insights['behavior_patterns']
        print(f"🎯 行为模式: {behavior.get('communication_style', 'unknown')}")
        print(f"📈 参与度: {behavior.get('engagement_level', 'unknown')}")
    
    if 'cognitive_state' in tom_insights:
        cognitive = tom_insights['cognitive_state']
        print(f"🎓 知识水平: {cognitive.get('knowledge_level', 'unknown')}")
        print(f"📚 学习风格: {cognitive.get('learning_style', 'unknown')}")
    
    # 显示完整的Memory prompt
    print(f"\n📋 完整Memory Prompt:")
    print("=" * 60)
    memory_prompt = updated_memory.to_prompt()
    print(memory_prompt)
    print("=" * 60)


def openai_example():
    """使用OpenAI API的示例（需要API Key）"""
    print("\n" + "=" * 60)
    print("🔑 OpenAI API示例 (需要API Key)")
    print("=" * 60)
    
    # 注意：这需要真实的OpenAI API Key
    api_key = "your-openai-api-key-here"  # 替换为真实的API Key
    
    if api_key == "your-openai-api-key-here":
        print("⚠️  请设置真实的OpenAI API Key才能运行此示例")
        print("💡 使用方法:")
        print("   api_key = 'sk-...'")
        print("   manager = create_openai_memory_manager(api_key)")
        return
    
    try:
        # 创建OpenAI驱动的Memory管理器
        openai_manager = create_openai_memory_manager(
            api_key=api_key,
            temperature=0.3,
            max_tokens=1500
        )
        
        conversation = [
            {'role': 'user', 'content': '我是一名数据科学家，专注于机器学习'},
            {'role': 'assistant', 'content': '数据科学是很有前景的领域！'},
        ]
        
        memory, result = openai_manager.update_memory_with_conversation(
            "openai_user", conversation
        )
        
        print("✅ OpenAI处理成功！")
        print(f"画像: {memory.get_profile_content()}")
        
    except Exception as e:
        print(f"❌ OpenAI API调用失败: {e}")
        print("💡 请检查API Key是否正确")


def simple_usage_example():
    """最简单的使用示例"""
    print("\n" + "=" * 60)
    print("⚡ 最简单的使用示例")
    print("=" * 60)
    
    # 一行代码创建Memory管理器
    manager = MemoryManager()
    
    # 你的conversation
    conversation = [
        {'role': 'user', 'content': '我是小明，喜欢游戏开发'},
        {'role': 'assistant', 'content': '游戏开发很有趣！'},
        {'role': 'user', 'content': '主要用Unity做手游'},
        {'role': 'assistant', 'content': 'Unity是很棒的引擎'}
    ]
    
    # 处理conversation并获取Memory prompt
    memory, _ = manager.update_memory_with_conversation("simple_user", conversation)
    
    print("🎯 结果:")
    print(memory.to_prompt())


if __name__ == "__main__":
    # 运行基础示例
    basic_conversation_example()
    
    # 运行OpenAI示例（需要API Key）
    openai_example()
    
    # 运行简单示例
    simple_usage_example()
    
    print(f"\n🎉 示例完成！")
    print(f"💡 PersonaLab支持多种使用方式：")
    print(f"   - 基础功能：无需API密钥即可使用")
    print(f"   - OpenAI集成：提供API密钥获得更智能的分析")
    print(f"   - 简洁API：一行代码即可开始使用") 