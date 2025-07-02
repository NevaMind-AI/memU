#!/usr/bin/env python3
"""
完整的人和Persona对话示例
演示所有记忆类型的使用，使用真正的OpenAI客户端进行对话
"""

import sys
sys.path.append('.')

from personalab import Persona
from personalab.llm import OpenAIClient

def print_separator(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_memory_section(title, content):
    """打印记忆部分"""
    print(f"\n📝 {title}:")
    print("-" * 40)
    if isinstance(content, list):
        if content:
            for i, item in enumerate(content, 1):
                print(f"  {i}. {item}")
        else:
            print("  暂无内容")
    else:
        print(f"  {content if content else '暂无内容'}")

def main():
    print_separator("🤖 完整的人与Persona对话示例 (使用OpenAI)")
    
    # 创建persona实例，使用真正的OpenAI客户端
    print("\n🚀 正在创建Persona...")
    print("💡 使用OpenAI客户端进行真实对话")
    
    # 方法1：让Persona自动创建默认的OpenAI客户端
    persona = Persona(
        agent_id="friendly_assistant",
        personality="我是一个友善、乐于助人的AI助手，喜欢与人交流并帮助解决问题。我会根据用户的背景和兴趣提供个性化的回复。",
        use_memo=False  # 暂时禁用memo功能专注于memory功能
    )
    
    user_id = "李明"
    
    # 第一阶段：添加用户的profile信息
    print_separator("👤 第一阶段：建立用户档案")
    print(f"正在添加用户 {user_id} 的基本信息...")
    
    persona.add_memory("我是一名全栈开发工程师", user_id=user_id, memory_type="profile")
    persona.add_memory("我在一家金融科技公司工作", user_id=user_id, memory_type="profile")
    persona.add_memory("我擅长Python、JavaScript和React", user_id=user_id, memory_type="profile")
    persona.add_memory("我喜欢学习新技术，经常参加技术分享会", user_id=user_id, memory_type="profile")
    persona.add_memory("我业余时间喜欢阅读、健身和旅行", user_id=user_id, memory_type="profile")
    
    print("✅ 用户档案建立完成")
    
    # 第二阶段：进行对话
    print_separator("💬 第二阶段：进行真实AI对话")
    
    # 对话内容
    conversations = [
        "你好！我是李明，很高兴认识你。",
        "能告诉我你的名字吗？你有什么特别的能力？",
        "我想聊聊我最近的工作情况。",
        "我对学习新技术很感兴趣，你有什么建议吗？",
        "我最近在考虑学习云计算，你觉得从哪里开始比较好？",
        "除了工作，我还喜欢健身和旅行，你有什么推荐吗？",
        "今天的对话很愉快，再见！"
    ]
    
    print(f"用户: {user_id}")
    print("Persona: friendly_assistant (OpenAI GPT)")
    print()
    
    # 进行真实的AI对话
    for i, user_message in enumerate(conversations, 1):
        print(f"👤 {user_id}: {user_message}")
        
        try:
            # 获取真实的AI回复
            response = persona.chat(user_message, user_id=user_id)
            print(f"🤖 Persona: {response}")
        except Exception as e:
            print(f"❌ 对话出错: {e}")
            print("💡 请检查OpenAI API配置和网络连接")
            break
        
        print()
        
        # 添加一些延迟效果
        import time
        time.sleep(1)
    
    # 第三阶段：手动添加事件记忆
    print_separator("📖 第三阶段：记录重要事件")
    print("正在记录对话中的重要事件...")
    
    # 手动添加一些事件记忆
    persona.add_memory("用户李明进行了自我介绍，表明身份为全栈开发工程师", user_id=user_id, memory_type="event")
    persona.add_memory("用户询问了关于学习新技术的建议", user_id=user_id, memory_type="event")
    persona.add_memory("用户表达了对云计算学习的兴趣", user_id=user_id, memory_type="event")
    persona.add_memory("用户分享了健身和旅行的个人爱好", user_id=user_id, memory_type="event")
    persona.add_memory("完成了一次完整的AI对话交流", user_id=user_id, memory_type="event")
    
    print("✅ 事件记录完成")
    
    # 第四阶段：添加心理洞察
    print_separator("🧠 第四阶段：生成心理洞察")
    print("正在分析用户特征并生成洞察...")
    
    # 手动添加一些心理洞察
    persona.add_memory("用户表现出强烈的学习欲望和技术好奇心", user_id=user_id, memory_type="mind")
    persona.add_memory("用户善于平衡工作与生活，追求全面发展", user_id=user_id, memory_type="mind")
    persona.add_memory("用户交流风格友善开放，愿意分享个人信息", user_id=user_id, memory_type="mind")
    persona.add_memory("用户具有前瞻性思维，关注新兴技术趋势", user_id=user_id, memory_type="mind")
    persona.add_memory("用户重视健康和体验，注重生活品质", user_id=user_id, memory_type="mind")
    
    print("✅ 心理洞察生成完成")
    
    # 第五阶段：结束会话
    print_separator("💾 第五阶段：结束会话")
    print(f"🔄 正在保存 {user_id} 的会话信息...")
    
    session_result = persona.endsession(user_id)
    print(f"✅ 会话结束: {session_result}")
    
    # 第六阶段：展示完整记忆
    print_separator("🧠 第六阶段：完整记忆展示")
    
    memory = persona.get_memory(user_id)
    
    # 打印Profile记忆
    print_memory_section("Profile记忆 (用户基本信息)", memory['profile'])
    
    # 打印Events记忆
    print_memory_section("Events记忆 (重要事件)", memory['events'])
    
    # 打印Mind记忆
    print_memory_section("Mind记忆 (心理洞察)", memory['mind'])
    
    # 详细统计信息
    print_separator("📊 记忆系统统计")
    
    # 计算记忆条目数
    profile_count = len(memory['profile']) if isinstance(memory['profile'], list) else (1 if memory['profile'] else 0)
    events_count = len(memory['events'])
    mind_count = len(memory['mind'])
    total_memories = profile_count + events_count + mind_count
    
    print(f"📋 Profile记忆: {profile_count} 条")
    print(f"📖 Events记忆: {events_count} 条")
    print(f"🧠 Mind记忆: {mind_count} 条")
    print(f"📚 总记忆条目: {total_memories} 条")
    
    # 展示记忆系统的价值
    print_separator("💡 记忆系统价值展示")
    
    print("🎯 基于记忆的个性化服务能力:")
    print(f"  • 了解用户职业背景：{memory['profile'][:50] if memory['profile'] else '暂无'}..." if memory['profile'] else "  • 职业背景：暂无信息")
    print(f"  • 记录重要事件：共{events_count}个关键事件")
    print(f"  • 心理特征分析：{mind_count}项深度洞察")
    
    print("\n🔮 未来对话的个性化基础:")
    if memory['events']:
        print("  • 可以基于用户的技术背景推荐学习资源")
        print("  • 可以询问云计算学习进展")
        print("  • 可以分享健身和旅行相关的内容")
        print("  • 可以继续技术话题的深入讨论")
    
    if memory['mind']:
        print("  • 了解用户的学习风格和动机")
        print("  • 知道用户重视工作生活平衡")
        print("  • 能够提供更贴合用户性格的建议")
        print("  • 可以预测用户可能感兴趣的话题")
    
    # 技术实现细节
    print_separator("🔧 技术实现说明")
    
    print("📝 记忆类型说明:")
    print("  • Profile: 存储用户基本信息、背景、特征等长期稳定的数据")
    print("  • Events: 记录用户的重要行为、决定、计划等时间性事件")
    print("  • Mind: 保存对用户性格、偏好、思维模式的分析洞察")
    
    print("\n🏗️ OpenAI集成优势:")
    print("  • 真实的AI对话体验，自然流畅的交流")
    print("  • 基于用户记忆的个性化回复")
    print("  • 上下文感知的智能响应")
    print("  • 持续学习用户偏好和特征")
    
    print("\n⚙️ 配置要求:")
    print("  • 需要设置 OPENAI_API_KEY 环境变量")
    print("  • 建议使用 gpt-3.5-turbo 或 gpt-4 模型")
    print("  • 确保网络连接可以访问 OpenAI API")
    
    print_separator("✨ 演示完成")
    print("🎉 恭喜！你已经完整体验了PersonaLab的真实AI对话和记忆系统")
    print("📚 本示例完整展示了:")
    print("   1. 👤 用户档案建立 (Profile)")
    print("   2. 💬 真实AI对话交流 (OpenAI GPT)")
    print("   3. 📖 事件记录管理 (Events)")
    print("   4. 🧠 心理洞察分析 (Mind)")
    print("   5. 💾 会话结束保存")
    print("   6. 🔍 记忆系统分析")
    print("\n🚀 PersonaLab + OpenAI = 拥有真正记忆的智能对话体验！")

if __name__ == "__main__":
    main() 