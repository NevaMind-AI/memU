#!/usr/bin/env python3
"""
02_conversation_recording.py

PersonaLab对话记录基础示例

演示如何：
1. 记录对话到数据库
2. 管理必须字段（user_id, agent_id, created_at）
3. 基本的对话存储和检索
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager


def main():
    print("=== PersonaLab 对话记录基础示例 ===\n")
    
    # 1. 创建对话管理器
    print("1. 创建对话管理器...")
    conversation_manager = ConversationManager(
        db_path="conversation_demo.db",
        enable_embeddings=False  # 暂时禁用embedding以简化示例
    )
    print("✅ 对话管理器创建成功\n")
    
    # 2. 记录第一个对话
    print("2. 记录第一个对话...")
    conversation_1 = conversation_manager.record_conversation(
        agent_id="customer_service",      # 必须字段：代理ID
        user_id="customer_001",           # 必须字段：用户ID
        messages=[
            {"role": "user", "content": "你好，我的订单还没有收到，能帮我查一下吗？"},
            {"role": "assistant", "content": "当然可以帮您查询。请提供您的订单号。"},
            {"role": "user", "content": "订单号是ORD-12345"},
            {"role": "assistant", "content": "好的，我查到您的订单正在配送中，预计明天下午送达。"}
        ],
        session_id="session_001"          # 可选：会话ID
    )
    
    print(f"✅ 对话记录成功")
    print(f"   对话ID: {conversation_1.conversation_id}")
    print(f"   代理ID: {conversation_1.agent_id}")
    print(f"   用户ID: {conversation_1.user_id}")
    print(f"   创建时间: {conversation_1.created_at}")
    print(f"   消息数量: {len(conversation_1.messages)}")
    print(f"   摘要: {conversation_1.summary}")
    print()
    
    # 3. 记录第二个对话（不同用户）
    print("3. 记录第二个对话（不同用户）...")
    conversation_2 = conversation_manager.record_conversation(
        agent_id="customer_service",
        user_id="customer_002",
        messages=[
            {"role": "user", "content": "我想退换一个商品，流程是怎样的？"},
            {"role": "assistant", "content": "退换商品很简单。请告诉我商品型号和购买时间。"},
            {"role": "user", "content": "是iPhone 15，上周五买的"},
            {"role": "assistant", "content": "好的，在7天内都可以无理由退换。我为您生成退换申请。"}
        ],
        session_id="session_002"
    )
    
    print(f"✅ 第二个对话记录成功")
    print(f"   对话ID: {conversation_2.conversation_id}")
    print(f"   用户ID: {conversation_2.user_id}")
    print(f"   摘要: {conversation_2.summary}")
    print()
    
    # 4. 记录第三个对话（同一用户，新会话）
    print("4. 记录第三个对话（同一用户，新会话）...")
    conversation_3 = conversation_manager.record_conversation(
        agent_id="customer_service",
        user_id="customer_001",  # 和第一个对话是同一用户
        messages=[
            {"role": "user", "content": "之前的订单已经收到了，谢谢！现在想买一个新产品"},
            {"role": "assistant", "content": "太好了！很高兴听到您满意我们的服务。请告诉我您想要什么产品？"}
        ],
        session_id="session_003"
    )
    
    print(f"✅ 第三个对话记录成功")
    print(f"   对话ID: {conversation_3.conversation_id}")
    print(f"   用户ID: {conversation_3.user_id}")
    print(f"   会话ID: {conversation_3.session_id}")
    print()
    
    # 5. 获取对话历史
    print("5. 获取对话历史...")
    
    # 获取所有对话
    all_conversations = conversation_manager.get_conversation_history(
        agent_id="customer_service",
        limit=10
    )
    print(f"✅ 找到 {len(all_conversations)} 个对话:")
    for i, conv in enumerate(all_conversations, 1):
        print(f"   {i}. ID: {conv['conversation_id'][:8]}...")
        print(f"      用户: {conv['user_id']}")
        print(f"      时间: {conv['created_at']}")
        print(f"      轮次: {conv['turn_count']}")
        print(f"      摘要: {conv['summary'][:50]}...")
        print()
    
    # 6. 按用户过滤对话
    print("6. 按用户过滤对话...")
    
    # customer_001的对话
    user_001_conversations = conversation_manager.get_conversation_history(
        agent_id="customer_service",
        user_id="customer_001",
        limit=10
    )
    print(f"✅ customer_001 的对话 ({len(user_001_conversations)} 个):")
    for conv in user_001_conversations:
        print(f"   - {conv['summary'][:60]}...")
    
    print()
    
    # customer_002的对话
    user_002_conversations = conversation_manager.get_conversation_history(
        agent_id="customer_service",
        user_id="customer_002",
        limit=10
    )
    print(f"✅ customer_002 的对话 ({len(user_002_conversations)} 个):")
    for conv in user_002_conversations:
        print(f"   - {conv['summary'][:60]}...")
    
    print()
    
    # 7. 获取完整对话详情
    print("7. 获取完整对话详情...")
    detailed_conversation = conversation_manager.get_conversation(conversation_1.conversation_id)
    
    if detailed_conversation:
        print(f"✅ 对话详情加载成功:")
        print(f"   对话ID: {detailed_conversation.conversation_id}")
        print(f"   代理ID: {detailed_conversation.agent_id}")
        print(f"   用户ID: {detailed_conversation.user_id}")
        print(f"   创建时间: {detailed_conversation.created_at}")
        print(f"   完整对话内容:")
        
        for i, message in enumerate(detailed_conversation.messages, 1):
            role_name = "客户" if message.role == "user" else "客服"
            print(f"     {i}. {role_name}: {message.content}")
    
    print()
    
    # 8. 按会话获取对话
    print("8. 按会话获取对话...")
    session_conversations = conversation_manager.get_session_conversations(
        agent_id="customer_service",
        session_id="session_001",
        user_id="customer_001"
    )
    
    print(f"✅ 会话 session_001 的对话 ({len(session_conversations)} 个):")
    for conv in session_conversations:
        print(f"   - 轮次: {conv.turn_count}")
        print(f"   - 摘要: {conv.summary}")
    
    print()
    
    # 9. 获取统计信息
    print("9. 获取统计信息...")
    stats = conversation_manager.get_conversation_stats("customer_service")
    
    print(f"✅ 对话统计信息:")
    print(f"   总对话数: {stats['total_conversations']}")
    print(f"   总会话数: {stats['total_sessions']}")
    print(f"   总轮次: {stats['total_turns']}")
    print(f"   平均轮次: {stats['average_turns_per_conversation']:.1f}")
    print(f"   最近对话: {stats['most_recent_conversation']}")
    
    # 10. 清理
    print("\n10. 清理资源...")
    conversation_manager.close()
    print("✅ 资源清理完成")
    
    print("\n=== 示例完成 ===")
    print("\n💡 学到的知识点:")
    print("1. ✅ 对话记录的必须字段：agent_id, user_id, created_at")
    print("2. ✅ 如何记录和管理对话历史")
    print("3. ✅ 按用户和会话过滤对话")
    print("4. ✅ 获取对话详情和统计信息")
    print("5. ✅ 对话数据的持久化存储")


if __name__ == "__main__":
    main() 