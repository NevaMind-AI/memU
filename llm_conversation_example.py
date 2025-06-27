"""
🚀 LLM驱动的PersonaLab Conversation示例

演示如何使用完全基于LLM的Memory更新系统，不使用任何规则性逻辑
"""

from personalab.memory import (
    MemoryManager, 
    create_llm_client,
    OpenAIClient,
    MockLLMClient
)

def create_llm_memory_manager(client_type="mock", **llm_config):
    """
    创建使用LLM的MemoryManager
    
    Args:
        client_type: LLM客户端类型 ("mock", "openai")
        **llm_config: LLM配置参数
    """
    # 创建LLM客户端
    llm_client = create_llm_client(client_type, **llm_config)
    
    # 创建使用LLM的MemoryManager
    memory_manager = MemoryManager(
        db_path=f"llm_{client_type}_memory.db",
        llm_client=llm_client,
        temperature=0.3,        # LLM参数
        max_tokens=2000
    )
    
    return memory_manager


def llm_conversation_example():
    """LLM驱动的conversation处理示例"""
    print("🤖 LLM驱动的Memory更新示例")
    print("=" * 60)
    
    # 创建LLM驱动的Memory管理器
    memory_manager = create_llm_memory_manager("mock")
    
    agent_id = "llm_agent_001"
    
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
    
    print(f"\n🔄 使用LLM Pipeline处理conversation...")
    
    # 使用LLM pipeline处理conversation
    updated_memory, llm_result = memory_manager.update_memory_with_conversation(
        agent_id, conversation
    )
    
    print(f"\n✅ LLM处理完成！")
    print("-" * 40)
    
    # 显示LLM pipeline结果
    print(f"📊 LLM Pipeline结果:")
    print(f"- 使用模型: {llm_result.pipeline_metadata.get('llm_model', 'unknown')}")
    print(f"- 画像更新: {llm_result.update_result.profile_updated}")
    print(f"- 事件添加: {llm_result.update_result.events_added}")
    print(f"- 分析置信度: {llm_result.modification_result.analysis_confidence:.2f}")
    print(f"- ToM置信度: {llm_result.tom_result.confidence_score:.2f}")
    
    # 显示LLM提取的信息
    print(f"\n🧠 LLM提取的画像更新:")
    print("-" * 30)
    for i, update in enumerate(llm_result.modification_result.profile_updates, 1):
        print(f"{i}. {update}")
    
    print(f"\n📝 LLM提取的事件:")
    print("-" * 30)
    for i, event in enumerate(llm_result.modification_result.events, 1):
        print(f"{i}. {event}")
    
    # 显示LLM更新后的画像
    print(f"\n👤 LLM更新后的用户画像:")
    print("-" * 40)
    print(updated_memory.get_profile_content())
    
    # 显示LLM的Theory of Mind分析
    print(f"\n🧠 LLM Theory of Mind分析:")
    print("-" * 40)
    tom_insights = llm_result.tom_result.insights
    
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
    print(f"\n📋 完整Memory Prompt (LLM生成):")
    print("=" * 60)
    memory_prompt = updated_memory.to_prompt()
    print(memory_prompt)
    print("=" * 60)
    
    # 显示原始LLM响应
    print(f"\n🔍 LLM原始响应 (调试用):")
    print("-" * 40)
    print("分析阶段响应:")
    print(llm_result.modification_result.raw_llm_response[:200] + "...")
    print("\n更新阶段响应:")
    print(llm_result.update_result.updated_profile_content[:200] + "...")
    print("\nToM分析响应:")
    print(llm_result.tom_result.raw_llm_response[:200] + "...")


def compare_pipelines_example():
    """对比LLM pipeline和规则pipeline的示例"""
    print("\n" + "=" * 60)
    print("🔄 LLM Pipeline vs 规则Pipeline对比")
    print("=" * 60)
    
    # 同一个conversation
    conversation = [
        {'role': 'user', 'content': '我是王小明，喜欢编程和音乐'},
        {'role': 'assistant', 'content': '编程和音乐都是很有创意的爱好！'},
        {'role': 'user', 'content': '是的，我用Python写代码，业余时间弹吉他'},
        {'role': 'assistant', 'content': 'Python很棒！你弹吉他多久了？'}
    ]
    
    # 1. LLM Pipeline
    print("🤖 LLM Pipeline处理结果:")
    print("-" * 30)
    
    llm_manager = create_llm_memory_manager("mock")
    llm_memory, llm_result = llm_manager.update_memory_with_conversation(
        "compare_llm", conversation
    )
    
    print(f"画像: {llm_memory.get_profile_content()}")
    print(f"事件数: {len(llm_memory.get_event_content())}")
    print(f"ToM洞察: {list(llm_result.tom_result.insights.keys())}")
    
    # 2. 规则Pipeline
    print(f"\n📏 规则Pipeline处理结果:")
    print("-" * 30)
    
    # 注意：现在已经没有规则pipeline了，只有LLM pipeline
    # 这里只是为了演示对比，实际上都是LLM驱动
    rule_manager = MemoryManager(
        db_path="rule_memory.db"
    )
    rule_memory, rule_result = rule_manager.update_memory_with_conversation(
        "compare_rule", conversation
    )
    
    print(f"画像: {rule_memory.get_profile_content()}")
    print(f"事件数: {len(rule_memory.get_event_content())}")
    print(f"ToM洞察: {list(rule_result.tom_result.insights.keys())}")
    
    print(f"\n💡 对比总结:")
    print(f"- 现在PersonaLab统一使用LLM Pipeline")
    print(f"- 所有Memory更新都是智能、自然的")


def openai_example():
    """使用OpenAI API的示例（需要API Key）"""
    print("\n" + "=" * 60)
    print("🔑 OpenAI API示例 (需要API Key)")
    print("=" * 60)
    
    # 注意：这需要真实的OpenAI API Key
    api_key = "your-openai-api-key-here"  # 替换为真实的API Key
    
    if api_key == "your-openai-api-key-here":
        print("⚠️  请设置真实的OpenAI API Key才能运行此示例")
        return
    
    try:
        # 创建OpenAI驱动的Memory管理器
        openai_manager = MemoryManager(
            db_path="openai_memory.db",
            llm_client=create_llm_client("openai", api_key=api_key),
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


def simple_llm_usage():
    """最简单的LLM使用方式"""
    print("\n" + "=" * 60)
    print("⚡ 最简单的LLM使用方式")
    print("=" * 60)
    
    # 一行代码创建Memory管理器（默认LLM驱动）
    manager = MemoryManager()
    
    # 你的conversation
    conversation = [
        {'role': 'user', 'content': '我叫张三，是个程序员'},
        {'role': 'assistant', 'content': '你好张三！'},
    ]
    
    # 一行代码处理
    memory, _ = manager.update_memory_with_conversation("simple", conversation)
    
    # 获取结果
    prompt = memory.to_prompt()
    print("🎯 结果:")
    print(prompt)


if __name__ == "__main__":
    # 运行主要示例
    llm_conversation_example()
    
    # 运行对比示例
    compare_pipelines_example()
    
    # 运行简单使用示例
    simple_llm_usage()
    
    # OpenAI示例（需要API Key）
    # openai_example()
    
    print(f"\n🎉 LLM驱动的Memory更新示例完成！")
    print(f"💡 现在PersonaLab完全使用LLM来进行Memory分析和更新，不再依赖规则性逻辑！") 