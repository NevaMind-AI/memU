"""
比较LLM-only搜索模式和keyword-fallback模式
Comparison between LLM-only and keyword-fallback search modes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab.main import Memory

def setup_test_memory(enable_llm=True):
    """设置测试记忆实例"""
    memory = Memory(
        agent_id=f"test_agent_{'llm' if enable_llm else 'keyword'}", 
        enable_llm_judgment=enable_llm
    )
    
    # 添加测试内容
    memory.agent_memory.profile.set_profile(
        "我是一个AI助手，专门帮助研究人员进行机器学习项目开发和优化。"
    )
    
    memory.agent_memory.events.add_memory(
        "帮助用户实现了一个基于BERT的文本分类模型，准确率达到94%"
    )
    memory.agent_memory.events.add_memory(
        "优化了深度学习训练流程，减少了30%的训练时间"
    )
    
    # 添加用户记忆
    user_memory = memory.get_user_memory("test_user")
    user_memory.profile.set_profile(
        "AI研究员，专注于自然语言处理和深度学习模型优化"
    )
    user_memory.events.add_memory(
        "正在进行BERT模型的参数高效微调研究"
    )
    
    return memory

def test_search_modes():
    """测试不同搜索模式"""
    print("=== PersonaLab搜索模式对比测试 ===\n")
    
    # 创建两种模式的记忆实例
    llm_memory = setup_test_memory(enable_llm=True)
    keyword_memory = setup_test_memory(enable_llm=False)
    
    print(f"LLM模式: {llm_memory}")
    print(f"关键词模式: {keyword_memory}")
    print()
    
    # 测试查询
    test_queries = [
        "我们的BERT模型优化进展如何？",
        "Help me with machine learning project",
        "深度学习训练时间问题",
        "What is the weather?",
        "继续我们之前关于模型效率的讨论"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. 查询: \"{query}\"")
        
        # LLM模式搜索决策
        llm_needs_search = llm_memory.need_search(query)
        print(f"   LLM模式决策: {'需要搜索' if llm_needs_search else '不需要搜索'}")
        
        # 关键词模式搜索决策
        keyword_needs_search = keyword_memory.need_search(query)
        print(f"   关键词模式决策: {'需要搜索' if keyword_needs_search else '不需要搜索'}")
        
        # 如果两种模式都需要搜索，比较搜索结果
        if llm_needs_search or keyword_needs_search:
            print("   搜索结果对比:")
            
            if llm_needs_search:
                llm_results = llm_memory.deep_search(query, user_id="test_user", max_results=2)
                print(f"     LLM模式: 找到{llm_results['results_found']}个结果")
                if llm_results['deep_search_metadata'].get('llm_analyzed'):
                    print(f"     ✅ 使用了LLM分析")
                else:
                    print(f"     ⚠️ 回退到关键词搜索")
            
            if keyword_needs_search:
                keyword_results = keyword_memory.deep_search(query, user_id="test_user", max_results=2)
                print(f"     关键词模式: 找到{keyword_results['results_found']}个结果")
                search_terms = keyword_results.get('search_terms', [])
                if search_terms:
                    print(f"     搜索词: {search_terms[:3]}")
        
        print()

if __name__ == "__main__":
    test_search_modes() 