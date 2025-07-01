#!/usr/bin/env python3
"""
03_semantic_search.py

PersonaLab语义搜索示例

演示如何：
1. 启用向量embedding功能
2. 记录对话并自动生成embedding
3. 使用语义搜索找到相关对话
4. 理解搜索相似度和阈值
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager


def main():
    print("=== PersonaLab 语义搜索示例 ===\n")
    
    # 1. 创建启用embedding的对话管理器
    print("1. 创建对话管理器（启用embedding）...")
    conversation_manager = ConversationManager(
        db_path="semantic_search_demo.db",
        enable_embeddings=True,           # 启用embedding
        embedding_provider="auto"         # 自动选择最佳provider
    )
    
    print(f"✅ 对话管理器创建成功")
    print(f"   Embedding Provider: {conversation_manager.embedding_manager.model_name}")
    print()
    
    # 2. 准备多个不同主题的对话
    print("2. 记录不同主题的对话...")
    
    conversations_data = [
        {
            "user_id": "student_001",
            "topic": "Python编程",
            "messages": [
                {"role": "user", "content": "我想学习Python编程，应该从哪里开始？"},
                {"role": "assistant", "content": "建议从Python基础语法开始，可以看官方教程和《Python Crash Course》这本书。"},
                {"role": "user", "content": "有什么在线练习网站推荐吗？"},
                {"role": "assistant", "content": "推荐Codecademy、LeetCode和HackerRank，都有很好的Python练习。"}
            ]
        },
        {
            "user_id": "student_002", 
            "topic": "机器学习",
            "messages": [
                {"role": "user", "content": "机器学习和深度学习有什么区别？"},
                {"role": "assistant", "content": "机器学习是更广泛的概念，深度学习是机器学习的一个子集，专门使用神经网络。"},
                {"role": "user", "content": "我该如何开始学习机器学习？"},
                {"role": "assistant", "content": "建议先学习Python和数学基础，然后使用scikit-learn练习传统机器学习算法。"}
            ]
        },
        {
            "user_id": "student_003",
            "topic": "网站开发",
            "messages": [
                {"role": "user", "content": "我想做一个网站，需要学什么技术？"},
                {"role": "assistant", "content": "前端需要HTML、CSS、JavaScript，后端可以选择Python Flask或Django。"},
                {"role": "user", "content": "有什么好的学习路径吗？"},
                {"role": "assistant", "content": "建议先学前端基础，再学后端框架，最后做项目实践。"}
            ]
        },
        {
            "user_id": "student_004",
            "topic": "数据分析",
            "messages": [
                {"role": "user", "content": "如何进行数据分析？需要什么工具？"},
                {"role": "assistant", "content": "数据分析主要用Python的pandas、numpy、matplotlib，或者R语言。"},
                {"role": "user", "content": "有推荐的学习资源吗？"},
                {"role": "assistant", "content": "推荐《Python数据科学手册》和Kaggle上的数据集练习。"}
            ]
        },
        {
            "user_id": "student_005",
            "topic": "移动开发",
            "messages": [
                {"role": "user", "content": "想开发手机App，应该选择什么技术？"},
                {"role": "assistant", "content": "可以选择原生开发（iOS/Android）或跨平台（React Native/Flutter）。"},
                {"role": "user", "content": "哪个更适合初学者？"},
                {"role": "assistant", "content": "建议从React Native开始，一套代码可以开发iOS和Android两个平台。"}
            ]
        }
    ]
    
    # 记录所有对话
    recorded_conversations = []
    for i, conv_data in enumerate(conversations_data, 1):
        print(f"   记录对话 {i}: {conv_data['topic']}")
        
        conversation = conversation_manager.record_conversation(
            agent_id="learning_assistant",
            user_id=conv_data["user_id"],
            messages=conv_data["messages"],
            enable_vectorization=True  # 确保生成embedding
        )
        
        recorded_conversations.append(conversation)
        print(f"   ✅ 对话ID: {conversation.conversation_id[:8]}...")
    
    print(f"\n✅ 共记录 {len(recorded_conversations)} 个对话\n")
    
    # 3. 测试不同的搜索查询
    print("3. 测试语义搜索...")
    
    search_queries = [
        "Python学习资源",
        "人工智能入门",
        "前端开发技术",
        "数据科学工具",
        "手机应用开发",
        "编程练习网站",
        "深度学习教程",
        "JavaScript框架"
    ]
    
    for query in search_queries:
        print(f"\n🔍 搜索查询: '{query}'")
        print("-" * 40)
        
        # 执行语义搜索
        results = conversation_manager.search_similar_conversations(
            agent_id="learning_assistant",
            query=query,
            limit=3,
            similarity_threshold=0.6  # 相似度阈值
        )
        
        if results:
            print(f"找到 {len(results)} 个相关对话:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. 相似度: {result['similarity_score']:.3f}")
                print(f"     用户: {result.get('user_id', 'N/A')}")
                print(f"     摘要: {result['summary'][:50]}...")
                
                # 显示匹配的内容片段
                if len(result['matched_content']) > 100:
                    print(f"     匹配内容: {result['matched_content'][:100]}...")
                else:
                    print(f"     匹配内容: {result['matched_content']}")
                print()
        else:
            print("❌ 没有找到相关对话")
    
    # 4. 测试不同相似度阈值的效果
    print("\n4. 测试不同相似度阈值...")
    
    test_query = "学习编程"
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    
    print(f"搜索查询: '{test_query}'")
    print("-" * 40)
    
    for threshold in thresholds:
        results = conversation_manager.search_similar_conversations(
            agent_id="learning_assistant",
            query=test_query,
            limit=5,
            similarity_threshold=threshold
        )
        
        print(f"阈值 {threshold}: 找到 {len(results)} 个结果")
        for result in results:
            print(f"  - 相似度: {result['similarity_score']:.3f}")
    
    print()
    
    # 5. 详细分析最佳匹配
    print("5. 详细分析最佳匹配...")
    
    detailed_query = "Python编程入门教程"
    print(f"查询: '{detailed_query}'")
    
    detailed_results = conversation_manager.search_similar_conversations(
        agent_id="learning_assistant",
        query=detailed_query,
        limit=1,
        similarity_threshold=0.0  # 获取最相似的结果
    )
    
    if detailed_results:
        best_match = detailed_results[0]
        conversation_detail = conversation_manager.get_conversation(best_match['conversation_id'])
        
        print(f"\n✅ 最佳匹配 (相似度: {best_match['similarity_score']:.3f}):")
        print(f"   对话ID: {conversation_detail.conversation_id}")
        print(f"   用户ID: {conversation_detail.user_id}")
        print(f"   创建时间: {conversation_detail.created_at}")
        print(f"   完整对话:")
        
        for i, message in enumerate(conversation_detail.messages, 1):
            role_name = "学生" if message.role == "user" else "助手"
            print(f"     {i}. {role_name}: {message.content}")
    
    print()
    
    # 6. 按用户搜索相关对话
    print("6. 按用户搜索相关对话...")
    
    user_query = "编程学习"
    user_id = "student_001"
    
    user_results = conversation_manager.search_similar_conversations(
        agent_id="learning_assistant",
        query=user_query,
        limit=5,
        similarity_threshold=0.5
    )
    
    # 过滤出指定用户的结果
    print(f"查询: '{user_query}' (所有用户)")
    for result in user_results:
        conversation_detail = conversation_manager.get_conversation(result['conversation_id'])
        print(f"  - 用户: {conversation_detail.user_id}, 相似度: {result['similarity_score']:.3f}")
    
    print()
    
    # 7. 搜索统计
    print("7. 搜索性能统计...")
    
    # 测试多个查询的性能
    import time
    
    performance_queries = ["Python", "机器学习", "网站", "数据", "手机"]
    total_time = 0
    total_results = 0
    
    for query in performance_queries:
        start_time = time.time()
        results = conversation_manager.search_similar_conversations(
            agent_id="learning_assistant",
            query=query,
            limit=3,
            similarity_threshold=0.6
        )
        end_time = time.time()
        
        search_time = end_time - start_time
        total_time += search_time
        total_results += len(results)
        
        print(f"  查询 '{query}': {len(results)} 个结果, 耗时 {search_time:.3f}s")
    
    print(f"\n✅ 性能统计:")
    print(f"   平均查询时间: {total_time/len(performance_queries):.3f}s")
    print(f"   平均结果数: {total_results/len(performance_queries):.1f}")
    
    # 8. 清理
    print("\n8. 清理资源...")
    conversation_manager.close()
    print("✅ 资源清理完成")
    
    print("\n=== 示例完成 ===")
    print("\n💡 学到的知识点:")
    print("1. ✅ 如何启用和配置embedding功能")
    print("2. ✅ 语义搜索的工作原理和效果")
    print("3. ✅ 相似度分数的含义和阈值设置")
    print("4. ✅ 不同查询策略的比较")
    print("5. ✅ 搜索性能的评估方法")


if __name__ == "__main__":
    main() 