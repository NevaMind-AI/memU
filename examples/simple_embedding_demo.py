#!/usr/bin/env python3
"""
简单的对话Embedding和召回演示

最基本的使用流程：
1. 输入一段对话
2. 存储并生成embedding
3. 输入查询语句
4. 召回相关对话
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager


def main():
    print("=== 简单对话Embedding召回演示 ===\n")
    
    # 初始化ConversationManager
    manager = ConversationManager(
        db_path="simple_demo.db",
        enable_embeddings=True
    )
    
    # 步骤1: 输入并存储一段对话
    print("📝 步骤1: 存储对话")
    print("-" * 30)
    
    # 对话内容
    conversation_messages = [
        {"role": "user", "content": "我想学习Python，应该从哪里开始？"},
        {"role": "assistant", "content": "建议从Python基础语法开始，可以看官方教程或《Python Crash Course》这本书。"},
        {"role": "user", "content": "有在线练习的网站吗？"},
        {"role": "assistant", "content": "推荐Codecademy、LeetCode和HackerRank，都有很好的Python练习题。"}
    ]
    
    # 存储对话
    conversation = manager.record_conversation(
        agent_id="demo_agent",
        user_id="demo_user", 
        messages=conversation_messages,
        enable_vectorization=True  # 生成embedding
    )
    
    print(f"✅ 对话已存储")
    print(f"   ID: {conversation.conversation_id}")
    print(f"   摘要: {conversation.summary}")
    print(f"   消息数: {len(conversation.messages)}")
    
    # 步骤2: 输入查询并召回
    print(f"\n🔍 步骤2: 查询召回")
    print("-" * 30)
    
    # 用户查询
    user_query = "Python学习资源"
    print(f"查询: '{user_query}'")
    
    # 召回相关对话
    similar_conversations = manager.search_similar_conversations(
        agent_id="demo_agent",
        query=user_query,
        limit=3,
        similarity_threshold=0.5
    )
    
    # 显示结果
    if similar_conversations:
        print(f"\n✅ 找到 {len(similar_conversations)} 个相关对话:")
        
        for i, result in enumerate(similar_conversations, 1):
            print(f"\n{i}. 相似度: {result['similarity_score']:.3f}")
            print(f"   摘要: {result['summary']}")
            
            # 获取完整对话
            full_conversation = manager.get_conversation(result['conversation_id'])
            print(f"   完整对话:")
            for msg in full_conversation.messages:
                role = "用户" if msg.role == "user" else "助手"
                print(f"     {role}: {msg.content}")
    else:
        print("❌ 没有找到相关对话")
    
    # 步骤3: 测试不同的查询
    print(f"\n🔍 步骤3: 测试更多查询")
    print("-" * 30)
    
    test_queries = [
        "编程练习网站",
        "学习资源推荐", 
        "在线编程教程",
        "Java入门"  # 不相关的查询
    ]
    
    for query in test_queries:
        print(f"\n查询: '{query}'")
        results = manager.search_similar_conversations(
            agent_id="demo_agent",
            query=query,
            limit=1,
            similarity_threshold=0.5
        )
        
        if results:
            score = results[0]['similarity_score']
            print(f"  ✅ 相似度: {score:.3f}")
            if score > 0.7:
                print(f"  💡 高度相关")
            elif score > 0.6:
                print(f"  💡 中度相关") 
            else:
                print(f"  💡 低度相关")
        else:
            print(f"  ❌ 无相关结果")
    
    print(f"\n=== 演示完成 ===")
    print(f"\n💡 使用说明:")
    print(f"1. 调用 record_conversation() 存储对话并自动生成embedding")
    print(f"2. 调用 search_similar_conversations() 根据查询召回相关对话")
    print(f"3. 系统会返回相似度分数，分数越高越相关")
    print(f"4. 可以设置 similarity_threshold 过滤低相关度结果")
    
    manager.close()


if __name__ == "__main__":
    main() 