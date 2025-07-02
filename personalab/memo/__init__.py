"""
PersonaLab Memo Module

Conversation recording, storage, and retrieval functionality:
- ConversationDB: Database operations for conversation storage
- ConversationManager: High-level conversation management
- Integration with vector embeddings for semantic search
- Memo: Simple API wrapper for conversation management
"""

from .storage import ConversationDB
from .manager import ConversationManager
from .models import Conversation, ConversationMessage

# Simple API wrapper
class Memo:
    """简洁的对话记忆管理API"""
    
    def __init__(self, agent_id: str, user_id: str = "default_user", data_dir: str = "data"):
        """初始化Memo
        
        Args:
            agent_id: 智能体ID
            user_id: 用户ID
            data_dir: 数据目录
        """
        self.agent_id = agent_id
        self.user_id = user_id
        import os
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, f"conversations.db")  # 使用统一的数据库文件
        self.manager = ConversationManager(db_path=db_path)
    
    def add_conversation(self, user_message: str, ai_response: str, metadata: dict = None):
        """添加对话"""
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ]
        return self.manager.record_conversation(
            agent_id=self.agent_id,
            user_id=self.user_id,
            messages=messages,
            pipeline_result=metadata  # metadata作为pipeline_result传递
        )
    
    def search_similar_conversations(self, query: str, top_k: int = 5, similarity_threshold: float = 0.6):
        """搜索相似对话"""
        return self.manager.search_similar_conversations(
            agent_id=self.agent_id,
            query=query,
            limit=top_k,
            similarity_threshold=similarity_threshold
        )
    
    @property
    def conversations(self):
        """获取所有对话"""
        return self.manager.get_conversation_history(agent_id=self.agent_id, user_id=self.user_id)
    
    def close(self):
        """关闭资源"""
        if hasattr(self.manager, 'close'):
            self.manager.close()

__all__ = [
    'ConversationDB',
    'ConversationManager', 
    'Conversation',
    'ConversationMessage',
    'Memo',  # 新增简洁API
] 