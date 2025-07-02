#!/usr/bin/env python3
"""
06_advanced_usage.py

PersonaLab高级用法示例

演示如何：
1. 批量处理大量对话数据
2. 多代理协作和知识共享
3. 高级分析和性能优化
4. 企业级应用场景
"""

import sys
from pathlib import Path
import time
import json
import random
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memory import MemoryClient
from personalab.memo import ConversationManager


class AdvancedPersonaLabManager:
    """高级PersonaLab管理器"""
    
    def __init__(self, memory_db: str, conversation_db: str):
        self.memory_manager = MemoryClient(db_path=memory_db)
        self.conversation_manager = ConversationManager(
            db_path=conversation_db,
            enable_embeddings=True,
            embedding_provider="auto"
        )
        self.agents = {}
        
    def create_agent_team(self, agent_configs: List[Dict]):
        """创建代理团队"""
        for config in agent_configs:
            agent_id = config['agent_id']
            memory = self.memory_manager.get_memory_by_agent(agent_id)
            memory.update_profile(config['profile'])
            
            if config.get('initial_events'):
                memory.update_events(config['initial_events'])
            
            if config.get('initial_insights'):
                memory.update_mind(config['initial_insights'])
            
            self.agents[agent_id] = {
                'memory': memory,
                'config': config,
                'stats': {'conversations': 0, 'messages': 0}
            }
            
            self.memory_manager.database.save_memory(memory)
        
        return self.agents
    
    def batch_process_conversations(self, conversations_data: List[Dict]):
        """批量处理对话数据"""
        
        results = []
        errors = []
        
        for conv_data in conversations_data:
            try:
                start_time = time.time()
                
                conversation = self.conversation_manager.record_conversation(
                    agent_id=conv_data['agent_id'],
                    user_id=conv_data['user_id'],
                    messages=conv_data['messages'],
                    session_id=conv_data.get('session_id'),
                    enable_vectorization=conv_data.get('enable_vectorization', True)
                )
                
                processing_time = time.time() - start_time
                
                # 更新代理统计
                if conv_data['agent_id'] in self.agents:
                    agent = self.agents[conv_data['agent_id']]
                    agent['stats']['conversations'] += 1
                    agent['stats']['messages'] += len(conv_data['messages'])
                
                results.append({
                    'success': True,
                    'conversation_id': conversation.conversation_id,
                    'agent_id': conversation.agent_id,
                    'user_id': conversation.user_id,
                    'turn_count': conversation.turn_count,
                    'processing_time': processing_time
                })
                
            except Exception as e:
                errors.append({
                    'success': False,
                    'error': str(e),
                    'conv_data': conv_data
                })
        
        return results, errors
    
    def knowledge_transfer(self, source_agent: str, target_agent: str, topic_keywords: List[str]):
        """代理间知识转移"""
        
        transferred_knowledge = {
            'events': [],
            'insights': [],
            'conversations': []
        }
        
        for keyword in topic_keywords:
            results = self.conversation_manager.search_similar_conversations(
                agent_id=source_agent,
                query=keyword,
                limit=3,
                similarity_threshold=0.7
            )
            
            for result in results:
                conversation_summary = f"从{source_agent}学习: {result['summary']}"
                transferred_knowledge['conversations'].append({
                    'summary': conversation_summary,
                    'similarity': result['similarity_score'],
                    'topic': keyword
                })
        
        # 更新目标代理的知识
        if target_agent in self.agents:
            target_memory = self.agents[target_agent]['memory']
            
            # 添加学习事件
            learning_events = [
                f"从代理{source_agent}学习了关于{keyword}的知识" 
                for keyword in topic_keywords
            ]
            target_memory.update_events(learning_events)
            transferred_knowledge['events'] = learning_events
            
            # 添加洞察
            learning_insights = [
                f"通过代理间知识共享，掌握了{source_agent}在{keyword}方面的经验"
                for keyword in topic_keywords
            ]
            target_memory.update_mind(learning_insights)
            transferred_knowledge['insights'] = learning_insights
            
            # 保存更新
            self.memory_manager.database.save_memory(target_memory)
        
        return transferred_knowledge
    
    def generate_agent_report(self, agent_id: str):
        """生成代理详细报告"""
        
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        memory = agent['memory']
        
        report = {
            'agent_id': agent_id,
            'profile': memory.get_profile_content(),
            'stats': agent['stats'].copy()
        }
        
        # 对话历史统计
        conversation_history = self.conversation_manager.get_conversation_history(
            agent_id=agent_id,
            limit=1000
        )
        
        if conversation_history:
            unique_users = set(conv['user_id'] for conv in conversation_history)
            report['user_stats'] = {
                'unique_users': len(unique_users),
                'total_conversations': len(conversation_history),
                'avg_conversations_per_user': len(conversation_history) / len(unique_users) if unique_users else 0
            }
        
        # 内存分析
        events = memory.get_event_content()
        insights = memory.get_mind_content()
        
        report['memory_analysis'] = {
            'total_events': len(events),
            'total_insights': len(insights),
            'recent_events': events[-3:] if events else [],
            'recent_insights': insights[-2:] if insights else []
        }
        
        return report
    
    def close(self):
        """关闭所有连接"""
        self.memory_manager.database.close()
        self.conversation_manager.close()


def main():
    print("=== PersonaLab 高级用法示例 ===\n")
    
    # 1. 初始化高级管理器
    print("1. 初始化高级管理器...")
    
    manager = AdvancedPersonaLabManager(
        memory_db="advanced_memory.db",
        conversation_db="advanced_conversations.db"
    )
    
    print("✅ 高级管理器初始化完成")
    print()
    
    # 2. 创建代理团队
    print("2. 创建专业代理团队...")
    
    agent_configs = [
        {
            "agent_id": "python_tutor",
            "profile": "我是专业的Python编程导师，专注于教授Python语言和编程基础。",
            "initial_events": ["专注于Python教学"],
            "initial_insights": ["学生需要循序渐进的学习"]
        },
        {
            "agent_id": "ml_expert", 
            "profile": "我是机器学习专家，专门指导机器学习算法和数据科学项目。",
            "initial_events": ["专注于ML教学"],
            "initial_insights": ["理论与实践结合重要"]
        },
        {
            "agent_id": "general_assistant",
            "profile": "我是通用AI助手，可以回答各种技术问题。",
            "initial_events": ["提供通用技术支持"],
            "initial_insights": ["用户问题多样化"]
        }
    ]
    
    agents = manager.create_agent_team(agent_configs)
    print(f"✅ 创建了 {len(agents)} 个专业代理:")
    for agent_id, agent_info in agents.items():
        print(f"   - {agent_id}: {agent_info['config']['profile'][:50]}...")
    print()
    
    # 3. 批量处理对话
    print("3. 批量处理对话数据...")
    
