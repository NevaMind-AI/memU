#!/usr/bin/env python3
"""
Conversation Embedding and Retrieval Example

演示如何：
1. 存储对话并生成embedding
2. 通过用户查询召回相关对话
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager


def main():
    """主要演示流程"""
    
    print("=== 对话Embedding和召回示例 ===\n")
    
    # 1. 初始化ConversationManager
    print("1. 初始化ConversationManager...")
    manager = ConversationManager(
        db_path="retrieval_demo.db",
        enable_embeddings=True,  # 启用embedding功能
        embedding_provider="auto"  # 自动选择最佳provider
    )
    
    print(f"✅ 使用embedding provider: {manager.embedding_manager.model_name}\n")
    
    # 2. 存储多个对话样本
    print("2. 存储对话样本并生成embedding...")
    
    conversations = [
        {
            "agent_id": "assistant",
            "user_id": "user_001", 
            "messages": [
                {"role": "user", "content": "我想学习Python编程，有什么好的资源推荐吗？"},
                {"role": "assistant", "content": "推荐几个学习Python的好资源：1. 官方文档 python.org 2. 《Python Crash Course》这本书 3. Codecademy的Python课程 4. LeetCode刷题练习"},
                {"role": "user", "content": "谢谢！我应该从哪里开始？"},
                {"role": "assistant", "content": "建议先从基础语法开始，可以看《Python Crash Course》的前几章，然后在Codecademy上做练习，最后用小项目巩固知识。"}
            ]
        },
        {
            "agent_id": "assistant", 
            "user_id": "user_002",
            "messages": [
                {"role": "user", "content": "我想做一个网站，应该学什么技术？"},
                {"role": "assistant", "content": "做网站需要学习：前端技术如HTML、CSS、JavaScript，后端可以选择Python Flask/Django、Node.js或Java Spring。数据库推荐MySQL或PostgreSQL。"},
                {"role": "user", "content": "我是初学者，推荐什么技术栈？"},
                {"role": "assistant", "content": "初学者推荐：HTML+CSS+JavaScript做前端，Python Flask做后端，SQLite数据库。这个组合学习曲线平缓，文档丰富。"}
            ]
        },
        {
            "agent_id": "assistant",
            "user_id": "user_003", 
            "messages": [
                {"role": "user", "content": "机器学习和深度学习有什么区别？"},
                {"role": "assistant", "content": "机器学习是更广泛的概念，包括线性回归、决策树、SVM等算法。深度学习是机器学习的子集，专门使用神经网络，特别是多层神经网络来解决复杂问题。"},
                {"role": "user", "content": "我想入门AI，应该先学什么？"},
                {"role": "assistant", "content": "建议学习路径：1. 先掌握Python和数学基础（线性代数、统计学） 2. 学习scikit-learn做传统机器学习 3. 再学TensorFlow或PyTorch做深度学习"}
            ]
        },
        {
            "agent_id": "assistant",
            "user_id": "user_004",
            "messages": [
                {"role": "user", "content": "怎么做数据分析？需要什么工具？"},
                {"role": "assistant", "content": "数据分析常用工具：Python的pandas、numpy、matplotlib，R语言，Excel，Tableau，Power BI。建议先学Python+pandas做数据清洗和分析。"},
                {"role": "user", "content": "有推荐的数据集练习吗？"},
                {"role": "assistant", "content": "推荐几个练习数据集：Kaggle竞赛数据、UCI机器学习数据库、政府开放数据、公司财报数据。可以从简单的销售数据或用户行为数据开始。"}
            ]
        }
    ]
    
    # 存储对话并生成embedding
    stored_conversations = []
    for i, conv_data in enumerate(conversations, 1):
        print(f"   存储对话 {i}...")
        conversation = manager.record_conversation(
            agent_id=conv_data["agent_id"],
            user_id=conv_data["user_id"],
            messages=conv_data["messages"],
            enable_vectorization=True  # 生成embedding
        )
        stored_conversations.append(conversation)
        print(f"   ✅ 对话ID: {conversation.conversation_id}")
        print(f"      摘要: {conversation.summary}")
    
    print(f"\n✅ 成功存储 {len(stored_conversations)} 个对话\n")
    
    # 3. 用户查询和召回
    print("3. 用户查询和召回演示...")
    
    queries = [
        "我想学编程",
        "网站开发技术栈", 
        "人工智能入门",
        "数据分析工具",
        "JavaScript教程"
    ]
    
    for query in queries:
        print(f"\n🔍 查询: '{query}'")
        print("-" * 40)
        
        # 搜索相似对话
        similar_conversations = manager.search_similar_conversations(
            agent_id="assistant",
            query=query,
            limit=3,
            similarity_threshold=0.6
        )
        
        if similar_conversations:
            print(f"找到 {len(similar_conversations)} 个相关对话:")
            
            for i, result in enumerate(similar_conversations, 1):
                print(f"\n  {i}. 相似度: {result['similarity_score']:.3f}")
                print(f"     对话ID: {result['conversation_id']}")
                print(f"     摘要: {result['summary']}")
                print(f"     匹配内容: {result['matched_content'][:100]}...")
        else:
            print("❌ 没有找到相关对话")
    
    # 4. 详细对话内容检索
    print(f"\n\n4. 详细对话内容检索演示...")
    
    query = "Python学习资源"
    print(f"\n🔍 详细查询: '{query}'")
    print("=" * 50)
    
    similar_conversations = manager.search_similar_conversations(
        agent_id="assistant", 
        query=query,
        limit=1,
        similarity_threshold=0.5
    )
    
    if similar_conversations:
        # 获取最相关的对话详情
        top_result = similar_conversations[0]
        conversation_detail = manager.get_conversation(top_result['conversation_id'])
        
        print(f"最相关对话 (相似度: {top_result['similarity_score']:.3f}):")
        print(f"用户ID: {conversation_detail.user_id}")
        print(f"创建时间: {conversation_detail.created_at}")
        print(f"消息数量: {len(conversation_detail.messages)}")
        print("\n完整对话内容:")
        print("-" * 30)
        
        for msg in conversation_detail.messages:
            role_name = "用户" if msg.role == "user" else "助手"
            print(f"{role_name}: {msg.content}")
            print()
    
    # 5. 统计信息
    print("5. 存储统计信息...")
    stats = manager.get_conversation_stats("assistant")
    
    print(f"\n📊 统计信息:")
    print(f"   总对话数: {stats['total_conversations']}")
    print(f"   总轮次: {stats['total_turns']}")
    print(f"   平均轮次: {stats['average_turns_per_conversation']:.1f}")
    print(f"   Embedding已启用: {stats['embedding_enabled']}")
    print(f"   Embedding模型: {stats['embedding_model']}")
    
    print("\n=== 示例完成 ===")
    print("\n💡 总结:")
    print("1. ✅ 成功存储多个对话并生成embedding")
    print("2. ✅ 通过用户查询成功召回相关对话")
    print("3. ✅ 展示了语义相似度搜索的效果") 
    print("4. ✅ 可以获取完整对话详情进行进一步处理")
    
    # 清理
    manager.close()


if __name__ == "__main__":
    main() 