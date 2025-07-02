"""
PersonaLab Memo Module

Conversation recording, storage, and retrieval functionality:
- ConversationManager: High-level conversation management
- Integration with vector embeddings for semantic search
- Memo: Simple API wrapper for conversation management

Note: Only PostgreSQL with pgvector is supported.
"""

import os

from ..config.database import get_database_manager
from .manager import ConversationManager
from .models import Conversation, ConversationMessage


# Simple API wrapper
class Memo:
    """简洁的对话记忆管理API"""

    def __init__(self, agent_id: str, user_id: str, data_dir: str = "data", db_manager=None):
        """Initialize Memo

        Args:
            agent_id: Agent identifier
            user_id: User identifier (required)
            data_dir: Directory to store vector database files
            (for backward compatibility)
            db_manager: Database manager instance. If None, will use global PostgreSQL manager
        """
        self.agent_id = agent_id
        self.user_id = user_id

        # 创建数据目录（向后兼容）
        os.makedirs(data_dir, exist_ok=True)

        # 使用数据库管理器
        if db_manager is not None:
            self.manager = ConversationManager(db_manager=db_manager)
        else:
            # 使用全局数据库管理器（PostgreSQL）
            db_manager = get_database_manager()
            self.manager = ConversationManager(db_manager=db_manager)

    def add_conversation(self, user_message: str, ai_response: str, metadata: dict = None):
        """添加对话"""
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response},
        ]
        return self.manager.record_conversation(
            agent_id=self.agent_id,
            user_id=self.user_id,
            messages=messages,
            pipeline_result=metadata,  # metadata作为pipeline_result传递
        )

    def search_similar_conversations(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.6
    ):
        """搜索相似对话"""
        return self.manager.search_similar_conversations(
            agent_id=self.agent_id,
            query=query,
            limit=top_k,
            similarity_threshold=similarity_threshold,
        )

    @property
    def conversations(self):
        """获取所有对话"""
        return self.manager.get_conversation_history(agent_id=self.agent_id, user_id=self.user_id)

    def close(self):
        """关闭资源"""
        if hasattr(self.manager, "close"):
            self.manager.close()


__all__ = [
    "ConversationManager",
    "Conversation", 
    "ConversationMessage",
    "Memo",  # 新增简洁API
]
