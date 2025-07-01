"""
PersonaLab Persona 智能体

提供简洁易用的PersonaLab智能体接口，模仿mem0.Memory的简洁API
"""

from ..utils import (
    create_memory_manager,
    create_conversation_manager,
    setup_agent_memory,
    get_memory_context,
    cleanup_memory_resources,
    chat_with_personalab
)


class Persona:
    """PersonaLab智能体类，模仿mem0.Memory的简洁API"""
    
    def __init__(self, openai_client=None, memory_db: str = "persona_memory.db", 
                 conversation_db: str = "persona_conversations.db"):
        """
        初始化Persona智能体
        
        Args:
            openai_client: OpenAI客户端，如果不提供会自动创建
            memory_db: 记忆数据库路径
            conversation_db: 对话数据库路径
        """
        # 自动创建OpenAI客户端（如果未提供）
        if openai_client is None:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI()
            except ImportError:
                raise ImportError("需要安装OpenAI库：pip install openai>=1.0.0")
        else:
            self.openai_client = openai_client
            
        # 创建PersonaLab组件
        self.memory_manager = create_memory_manager(memory_db)
        self.conversation_manager = create_conversation_manager(conversation_db)
        
    def chat(self, message: str, agent_id: str = "default_agent", user_id: str = "default_user") -> str:
        """
        与智能体聊天，自动管理记忆和学习
        
        Args:
            message: 用户消息
            agent_id: 智能体ID
            user_id: 用户ID
            
        Returns:
            str: 智能体回复
        """
        return chat_with_personalab(
            self.openai_client, self.memory_manager, self.conversation_manager,
            message, agent_id, user_id
        )
    
    def search(self, query: str, agent_id: str = "default_agent", limit: int = 3, 
               similarity_threshold: float = 0.6) -> list:
        """
        搜索相关记忆对话
        
        Args:
            query: 搜索查询
            agent_id: 智能体ID  
            limit: 返回结果数量限制
            similarity_threshold: 相似度阈值
            
        Returns:
            list: 搜索结果列表
        """
        try:
            results = self.conversation_manager.search_similar_conversations(
                agent_id=agent_id, query=query, limit=limit, 
                similarity_threshold=similarity_threshold
            )
            return results
        except:
            return []
    
    def add_memory(self, content: str, agent_id: str = "default_agent"):
        """
        手动添加记忆内容
        
        Args:
            content: 记忆内容
            agent_id: 智能体ID
        """
        try:
            setup_agent_memory(self.memory_manager, agent_id, content)
        except:
            pass
    
    def get_memory(self, agent_id: str = "default_agent") -> str:
        """
        获取智能体记忆摘要
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            str: 记忆摘要
        """
        return get_memory_context(self.memory_manager, agent_id)
    
    def close(self):
        """关闭并清理资源"""
        cleanup_memory_resources(self.memory_manager, self.conversation_manager) 