#!/usr/bin/env python3
"""
05_integration.py

PersonaLab Memory和Memo模块集成示例

演示如何：
1. 结合使用Memory（内存管理）和Memo（对话记录）
2. 根据对话历史更新AI代理内存
3. 使用内存状态影响对话响应
4. 实现完整的AI代理学习循环
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memory import MemoryClient
from personalab.memo import ConversationManager
from utils import (
    simulate_ai_response,
    extract_events_from_conversation,
    extract_insights_from_conversation
)
from datetime import datetime


# 注意：simulate_ai_response, extract_insights_from_conversation, extract_events_from_conversation
# 这些函数已经从utils模块导入，避免重复定义


def main():
    print("=== PersonaLab Memory+Memo 集成示例 ===\n")
    
    # 1. 初始化两个管理器
    print("1. 初始化Memory和Memo管理器...")
    
    memory_manager = MemoryClient(db_path="integration_memory.db")
    conversation_manager = ConversationManager(
        db_path="integration_conversations.db",
        enable_embeddings=True,
        embedding_provider="auto"
    )
    
    print("✅ 管理器初始化完成")
    print(f"   Memory DB: integration_memory.db")
    print(f"   Conversation DB: integration_conversations.db")
    print(f"   Embedding Provider: {conversation_manager.embedding_manager.model_name}")
    print()
    
    # 2. 创建AI代理
    print("2. 创建AI代理...")
    
    agent_id = "learning_tutor"
    user_id = "student_zhang"
    
    # 初始化代理内存
    memory = memory_manager.get_memory_by_agent(agent_id)
    memory.update_profile("我是一个智能学习导师，专门帮助用户学习编程和技术知识。我会记住用户的学习进度和偏好。")
    
    print(f"✅ AI代理创建完成")
    print(f"   代理ID: {agent_id}")
    print(f"   用户ID: {user_id}")
    print(f"   初始Profile: {memory.get_profile_content()}")
    print()
    
    # 3. 模拟完整的对话会话
    print("3. 模拟完整的对话会话...")
    
    conversation_sessions = [
        {
            "session_id": "session_001",
            "topic": "初次见面",
            "user_messages": [
                "你好，我想学习编程，但是完全没有基础",
                "应该从哪种编程语言开始？",
                "Python难学吗？",
                "好的，我想从Python开始学习"
            ]
        },
        {
            "session_id": "session_002", 
            "topic": "Python学习",
            "user_messages": [
                "我已经看完了Python基础教程，想做个项目练习",
                "有什么简单的项目推荐吗？",
                "计算器项目具体应该怎么做？",
                "谢谢，我会尝试做这个项目的"
            ]
        },
        {
            "session_id": "session_003",
            "topic": "进阶学习",
            "user_messages": [
                "我的计算器项目做完了，想学习更高级的内容",
                "对机器学习很感兴趣，但不知道从哪里开始",
                "需要什么数学基础吗？",
                "好的，我会先学习这些数学知识"
            ]
        }
    ]
    
    all_conversations = []
    
    for session in conversation_sessions:
        print(f"\n📱 会话: {session['topic']} ({session['session_id']})")
        print("-" * 40)
        
        session_messages = []
        
        for user_message in session["user_messages"]:
            # 生成AI响应
            ai_response = simulate_ai_response(memory, user_message)
            
            # 添加到会话消息
            session_messages.extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_response}
            ])
            
            # 显示对话
            print(f"👤 用户: {user_message}")
            print(f"🤖 助手: {ai_response}")
            print()
        
        # 记录完整对话
        conversation = conversation_manager.record_conversation(
            agent_id=agent_id,
            user_id=user_id,
            messages=session_messages,
            session_id=session["session_id"]
        )
        
        all_conversations.append(conversation)
        print(f"✅ 对话已记录 (ID: {conversation.conversation_id[:8]}...)")
        
        # 从对话中学习和更新内存
        print("🧠 更新AI内存...")
        
        # 提取新的事件
        new_events = extract_events_from_conversation(session_messages)
        if new_events:
            memory.update_events(new_events)
            print(f"   添加事件: {len(new_events)} 个")
            for event in new_events:
                print(f"     - {event}")
        
        # 提取新的洞察
        current_insights = memory.get_mind_content()
        new_insights = extract_insights_from_conversation(session_messages, current_insights)
        if new_insights:
            memory.update_mind(new_insights)
            print(f"   添加洞察: {len(new_insights)} 个")
            for insight in new_insights:
                print(f"     - {insight}")
        
        # 保存内存状态
        memory_manager.database.save_memory(memory)
        print("   内存状态已保存")
        print()
    
    # 4. 查看AI代理的完整学习记录
    print("4. AI代理的完整学习记录...")
    print("=" * 50)
    print(memory.to_prompt())
    print("=" * 50)
    print()
    
    # 5. 基于历史对话的智能检索
    print("5. 基于历史对话的智能检索...")
    
    search_queries = [
        "Python学习方法",
        "项目实践经验", 
        "机器学习入门",
        "用户的学习进度"
    ]
    
    for query in search_queries:
        print(f"\n🔍 搜索: '{query}'")
        
        # 搜索相关对话
        results = conversation_manager.search_similar_conversations(
            agent_id=agent_id,
            query=query,
            limit=2,
            similarity_threshold=0.6
        )
        
        if results:
            print(f"找到 {len(results)} 个相关对话:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. 相似度: {result['similarity_score']:.3f}")
                print(f"     摘要: {result['summary'][:60]}...")
                print(f"     匹配内容: {result['matched_content'][:80]}...")
        else:
            print("没有找到相关对话")
    
    # 6. 智能问答：结合内存和历史对话
    print("\n6. 智能问答：结合内存和历史对话...")
    
    test_questions = [
        "用户之前问过什么问题？",
        "用户的学习偏好是什么？",
        "推荐下一步学习内容",
        "用户完成了哪些项目？"
    ]
    
    for question in test_questions:
        print(f"\n❓ 问题: {question}")
        
        # 1. 从内存获取信息
        profile = memory.get_profile_content()
        events = memory.get_event_content()[-3:]  # 最近事件
        insights = memory.get_mind_content()[-2:]  # 最近洞察
        
        # 2. 搜索相关对话
        search_results = conversation_manager.search_similar_conversations(
            agent_id=agent_id,
            query=question,
            limit=2,
            similarity_threshold=0.5
        )
        
        # 3. 综合回答
        print("📊 信息来源:")
        print(f"   内存事件: {'; '.join(events) if events else '无'}")
        print(f"   用户洞察: {'; '.join(insights) if insights else '无'}")
        if search_results:
            print(f"   相关对话: {len(search_results)} 个")
            for result in search_results:
                print(f"     - {result['summary'][:50]}...")
        else:
            print("   相关对话: 无")
        
        # 生成智能回答
        ai_answer = simulate_ai_response(memory, question, search_results)
        print(f"🤖 回答: {ai_answer}")
    
    # 7. 用户成长轨迹分析
    print("\n7. 用户成长轨迹分析...")
    
    # 获取所有对话历史
    conversation_history = conversation_manager.get_conversation_history(
        agent_id=agent_id,
        user_id=user_id,
        limit=10
    )
    
    print(f"📈 用户 {user_id} 的成长轨迹:")
    print(f"   总对话数: {len(conversation_history)}")
    print(f"   总轮次: {sum(conv['turn_count'] for conv in conversation_history)}")
    
    # 按时间顺序显示学习进展
    print(f"\n时间线:")
    for i, conv in enumerate(reversed(conversation_history), 1):
        print(f"   {i}. {conv['created_at'][:16]} - {conv['summary'][:50]}...")
    
    # 显示内存中的学习轨迹
    print(f"\n学习事件记录:")
    for i, event in enumerate(memory.get_event_content(), 1):
        print(f"   {i}. {event}")
    
    print(f"\n用户特征洞察:")
    for i, insight in enumerate(memory.get_mind_content(), 1):
        print(f"   {i}. {insight}")
    
    # 8. 模拟新对话（基于完整历史）
    print("\n8. 模拟新对话（基于完整历史）...")
    
    new_user_message = "我现在想找一份Python开发工作，需要准备什么？"
    print(f"👤 用户: {new_user_message}")
    
    # 基于完整内存状态生成响应
    contextual_response = simulate_ai_response(memory, new_user_message)
    print(f"🤖 助手: {contextual_response}")
    
    # 搜索相关的历史对话
    job_related_conversations = conversation_manager.search_similar_conversations(
        agent_id=agent_id,
        query="工作 职业 开发",
        limit=3,
        similarity_threshold=0.4
    )
    
    print(f"\n📚 相关历史对话:")
    if job_related_conversations:
        for result in job_related_conversations:
            print(f"   - 相似度: {result['similarity_score']:.3f}")
            print(f"     内容: {result['matched_content'][:60]}...")
    else:
        print("   未找到直接相关的历史对话，但基于用户学习轨迹可以给出建议")
    
    # 9. 清理资源
    print("\n9. 清理资源...")
    memory_manager.database.close()
    conversation_manager.close()
    print("✅ 资源清理完成")
    
    print("\n=== 示例完成 ===")
    print("\n💡 学到的知识点:")
    print("1. ✅ Memory和Memo模块的协同工作")
    print("2. ✅ 从对话中自动提取事件和洞察")
    print("3. ✅ 基于内存状态生成个性化响应")
    print("4. ✅ 结合历史对话的智能检索")
    print("5. ✅ 用户成长轨迹的记录和分析")
    print("6. ✅ 实现完整的AI代理学习循环")


if __name__ == "__main__":
    main() 