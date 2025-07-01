#!/usr/bin/env python3
"""
04_user_management.py

PersonaLab用户管理示例

演示如何：
1. 管理多个用户的对话历史
2. 按用户过滤对话和搜索
3. 用户会话管理
4. 用户统计分析
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager
from datetime import datetime, timedelta


def main():
    print("=== PersonaLab 用户管理示例 ===\n")
    
    # 1. 创建对话管理器
    print("1. 创建对话管理器...")
    conversation_manager = ConversationManager(
        db_path="user_management_demo.db",
        enable_embeddings=True,
        embedding_provider="auto"
    )
    
    print(f"✅ 对话管理器创建成功")
    print(f"   Embedding Provider: {conversation_manager.embedding_manager.model_name}")
    print()
    
    # 2. 创建多个用户的对话数据
    print("2. 创建多用户对话数据...")
    
    # 用户数据定义
    users_data = {
        "alice_chen": {
            "name": "Alice Chen",
            "role": "数据科学家",
            "interests": ["Python", "机器学习", "数据分析"]
        },
        "bob_smith": {
            "name": "Bob Smith", 
            "role": "前端开发工程师",
            "interests": ["JavaScript", "React", "Web设计"]
        },
        "charlie_wang": {
            "name": "Charlie Wang",
            "role": "学生",
            "interests": ["编程入门", "计算机基础", "项目实践"]
        },
        "diana_liu": {
            "name": "Diana Liu",
            "role": "产品经理",
            "interests": ["技术趋势", "AI应用", "产品设计"]
        }
    }
    
    # 为每个用户创建对话
    user_conversations = {}
    
    # Alice - 数据科学家的对话
    print("   创建Alice的对话（数据科学主题）...")
    alice_conversations = [
        {
            "session": "morning_work",
            "messages": [
                {"role": "user", "content": "我需要分析一个大型数据集，应该用什么工具？"},
                {"role": "assistant", "content": "对于大型数据集，建议使用pandas处理结构化数据，或者Dask处理超大数据集。"},
                {"role": "user", "content": "Dask和pandas有什么区别？"},
                {"role": "assistant", "content": "Dask可以处理超过内存大小的数据，支持并行计算，而pandas适合单机内存内的数据。"}
            ]
        },
        {
            "session": "afternoon_learning",
            "messages": [
                {"role": "user", "content": "我想学习深度学习，从哪里开始？"},
                {"role": "assistant", "content": "建议从TensorFlow或PyTorch开始，先学习基础的神经网络概念。"},
                {"role": "user", "content": "有什么好的实践项目推荐？"},
                {"role": "assistant", "content": "可以从图像分类开始，使用CIFAR-10数据集，然后尝试自然语言处理任务。"}
            ]
        }
    ]
    
    user_conversations["alice_chen"] = []
    for conv in alice_conversations:
        conversation = conversation_manager.record_conversation(
            agent_id="ai_assistant",
            user_id="alice_chen",
            messages=conv["messages"],
            session_id=conv["session"]
        )
        user_conversations["alice_chen"].append(conversation)
    
    # Bob - 前端开发工程师的对话
    print("   创建Bob的对话（前端开发主题）...")
    bob_conversations = [
        {
            "session": "react_learning", 
            "messages": [
                {"role": "user", "content": "React的useState和useEffect有什么区别？"},
                {"role": "assistant", "content": "useState管理组件状态，useEffect处理副作用如API调用、事件监听等。"},
                {"role": "user", "content": "能给个useEffect的具体例子吗？"},
                {"role": "assistant", "content": "比如useEffect(() => { fetchData(); }, [])在组件挂载时获取数据。"}
            ]
        },
        {
            "session": "performance_optimization",
            "messages": [
                {"role": "user", "content": "如何优化React应用的性能？"},
                {"role": "assistant", "content": "可以使用React.memo、useMemo、useCallback避免不必要的重渲染。"},
                {"role": "user", "content": "代码分割也能提升性能吗？"},
                {"role": "assistant", "content": "是的，使用React.lazy和Suspense可以按需加载组件，减少初始包大小。"}
            ]
        }
    ]
    
    user_conversations["bob_smith"] = []
    for conv in bob_conversations:
        conversation = conversation_manager.record_conversation(
            agent_id="ai_assistant",
            user_id="bob_smith", 
            messages=conv["messages"],
            session_id=conv["session"]
        )
        user_conversations["bob_smith"].append(conversation)
    
    # Charlie - 学生的对话
    print("   创建Charlie的对话（编程入门主题）...")
    charlie_conversations = [
        {
            "session": "programming_basics",
            "messages": [
                {"role": "user", "content": "我是编程新手，应该学哪种语言？"},
                {"role": "assistant", "content": "Python是很好的入门选择，语法简单，应用广泛。"},
                {"role": "user", "content": "学会Python后能做什么？"},
                {"role": "assistant", "content": "可以做网站开发、数据分析、机器学习、自动化脚本等。"}
            ]
        },
        {
            "session": "first_project",
            "messages": [
                {"role": "user", "content": "我想做第一个Python项目，有什么建议？"},
                {"role": "assistant", "content": "建议做一个简单的计算器或待办事项管理器，能练习基础语法。"},
                {"role": "user", "content": "需要什么开发工具？"},
                {"role": "assistant", "content": "VS Code是很好的编辑器，配合Python扩展使用。"}
            ]
        }
    ]
    
    user_conversations["charlie_wang"] = []
    for conv in charlie_conversations:
        conversation = conversation_manager.record_conversation(
            agent_id="ai_assistant",
            user_id="charlie_wang",
            messages=conv["messages"], 
            session_id=conv["session"]
        )
        user_conversations["charlie_wang"].append(conversation)
    
    # Diana - 产品经理的对话
    print("   创建Diana的对话（AI产品主题）...")
    diana_conversations = [
        {
            "session": "ai_trends",
            "messages": [
                {"role": "user", "content": "当前AI技术有哪些值得关注的趋势？"},
                {"role": "assistant", "content": "大语言模型、多模态AI、AI绘画、自动驾驶等都是热门领域。"},
                {"role": "user", "content": "如何在产品中集成AI功能？"},
                {"role": "assistant", "content": "可以从用户痛点出发，选择合适的AI能力，如智能推荐、自然语言处理等。"}
            ]
        }
    ]
    
    user_conversations["diana_liu"] = []
    for conv in diana_conversations:
        conversation = conversation_manager.record_conversation(
            agent_id="ai_assistant",
            user_id="diana_liu",
            messages=conv["messages"],
            session_id=conv["session"]
        )
        user_conversations["diana_liu"].append(conversation)
    
    print(f"\n✅ 共为 {len(users_data)} 个用户创建了对话\n")
    
    # 3. 按用户查看对话历史
    print("3. 按用户查看对话历史...")
    
    for user_id, user_info in users_data.items():
        print(f"\n👤 用户: {user_info['name']} ({user_id})")
        print(f"   角色: {user_info['role']}")
        print(f"   兴趣: {', '.join(user_info['interests'])}")
        
        # 获取该用户的对话历史
        user_history = conversation_manager.get_conversation_history(
            agent_id="ai_assistant",
            user_id=user_id,
            limit=10
        )
        
        print(f"   对话数量: {len(user_history)}")
        for i, conv in enumerate(user_history, 1):
            print(f"     {i}. {conv['summary'][:50]}...")
            print(f"        时间: {conv['created_at']}")
            print(f"        轮次: {conv['turn_count']}")
    
    print()
    
    # 4. 按用户进行语义搜索
    print("4. 按用户进行语义搜索...")
    
    search_scenarios = [
        {
            "query": "机器学习",
            "description": "查找关于机器学习的对话"
        },
        {
            "query": "React开发",
            "description": "查找关于React开发的对话"
        },
        {
            "query": "编程入门",
            "description": "查找关于编程入门的对话"
        },
        {
            "query": "AI产品",
            "description": "查找关于AI产品的对话"
        }
    ]
    
    for scenario in search_scenarios:
        print(f"\n🔍 搜索: '{scenario['query']}' - {scenario['description']}")
        print("-" * 50)
        
        # 全局搜索
        global_results = conversation_manager.search_similar_conversations(
            agent_id="ai_assistant",
            query=scenario["query"],
            limit=5,
            similarity_threshold=0.6
        )
        
        print(f"全局搜索结果 ({len(global_results)} 个):")
        for result in global_results:
            # 获取用户信息
            conv_detail = conversation_manager.get_conversation(result['conversation_id'])
            user_name = users_data.get(conv_detail.user_id, {}).get('name', conv_detail.user_id)
            
            print(f"  - 用户: {user_name}")
            print(f"    相似度: {result['similarity_score']:.3f}")
            print(f"    摘要: {result['summary'][:60]}...")
    
    print()
    
    # 5. 用户会话分析
    print("5. 用户会话分析...")
    
    for user_id, user_info in users_data.items():
        print(f"\n📊 {user_info['name']} 的会话分析:")
        
        # 获取用户所有对话
        user_conversations_list = conversation_manager.get_conversation_history(
            agent_id="ai_assistant",
            user_id=user_id,
            limit=100
        )
        
        if user_conversations_list:
            # 会话统计
            sessions = set()
            total_turns = 0
            latest_time = None
            
            for conv in user_conversations_list:
                if conv.get('session_id'):
                    sessions.add(conv['session_id'])
                total_turns += conv.get('turn_count', 0)
                
                # 找到最新对话时间
                conv_time = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00').replace('+00:00', ''))
                if latest_time is None or conv_time > latest_time:
                    latest_time = conv_time
            
            print(f"   总对话数: {len(user_conversations_list)}")
            print(f"   会话数: {len(sessions)}")
            print(f"   总轮次: {total_turns}")
            print(f"   平均轮次: {total_turns/len(user_conversations_list):.1f}")
            print(f"   最近活动: {latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else 'N/A'}")
            
            # 获取会话详情
            print(f"   会话详情:")
            for session_id in sessions:
                session_convs = conversation_manager.get_session_conversations(
                    agent_id="ai_assistant",
                    session_id=session_id,
                    user_id=user_id
                )
                session_turns = sum(conv.turn_count for conv in session_convs)
                print(f"     - {session_id}: {len(session_convs)} 对话, {session_turns} 轮次")
        else:
            print("   暂无对话记录")
    
    # 6. 跨用户对话分析
    print("\n6. 跨用户对话分析...")
    
    # 获取所有对话统计
    all_conversations = conversation_manager.get_conversation_history(
        agent_id="ai_assistant",
        limit=1000
    )
    
    # 按用户分组统计
    user_stats = {}
    for conv in all_conversations:
        user_id = conv['user_id']
        if user_id not in user_stats:
            user_stats[user_id] = {
                'conversations': 0,
                'total_turns': 0,
                'sessions': set()
            }
        
        user_stats[user_id]['conversations'] += 1
        user_stats[user_id]['total_turns'] += conv.get('turn_count', 0)
        if conv.get('session_id'):
            user_stats[user_id]['sessions'].add(conv['session_id'])
    
    print(f"📈 总体统计:")
    print(f"   总用户数: {len(user_stats)}")
    print(f"   总对话数: {len(all_conversations)}")
    print(f"   总轮次: {sum(stats['total_turns'] for stats in user_stats.values())}")
    
    print(f"\n用户活跃度排名:")
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['conversations'], reverse=True)
    for i, (user_id, stats) in enumerate(sorted_users, 1):
        user_name = users_data.get(user_id, {}).get('name', user_id)
        print(f"   {i}. {user_name}: {stats['conversations']} 对话, {stats['total_turns']} 轮次")
    
    # 7. 用户兴趣分析（基于对话内容）
    print("\n7. 用户兴趣分析...")
    
    interest_keywords = {
        "数据科学": ["数据", "分析", "pandas", "numpy", "机器学习", "深度学习"],
        "前端开发": ["React", "JavaScript", "HTML", "CSS", "前端", "组件"],
        "编程基础": ["编程", "Python", "入门", "语法", "项目", "学习"],
        "AI技术": ["AI", "人工智能", "模型", "算法", "趋势", "应用"]
    }
    
    for user_id, user_info in users_data.items():
        print(f"\n🎯 {user_info['name']} 的兴趣分析:")
        
        # 获取用户所有对话内容
        user_conversations_list = conversation_manager.get_conversation_history(
            agent_id="ai_assistant", 
            user_id=user_id,
            limit=100
        )
        
        # 收集所有对话文本
        all_text = ""
        for conv_summary in user_conversations_list:
            conv_detail = conversation_manager.get_conversation(conv_summary['conversation_id'])
            if conv_detail:
                for message in conv_detail.messages:
                    all_text += message.content + " "
        
        # 分析兴趣匹配
        interest_scores = {}
        for interest, keywords in interest_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in all_text.lower())
            if score > 0:
                interest_scores[interest] = score
        
        # 显示兴趣排名
        if interest_scores:
            sorted_interests = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)
            print(f"   检测到的兴趣领域:")
            for interest, score in sorted_interests:
                print(f"     - {interest}: {score} 次提及")
        else:
            print(f"   未检测到明显的兴趣模式")
    
    # 8. 清理
    print("\n8. 清理资源...")
    conversation_manager.close()
    print("✅ 资源清理完成")
    
    print("\n=== 示例完成 ===")
    print("\n💡 学到的知识点:")
    print("1. ✅ 如何管理多个用户的对话数据")
    print("2. ✅ 按用户过滤对话历史和搜索结果")
    print("3. ✅ 用户会话管理和统计分析")
    print("4. ✅ 跨用户数据分析和用户活跃度计算")
    print("5. ✅ 基于对话内容的用户兴趣分析")


if __name__ == "__main__":
    main() 