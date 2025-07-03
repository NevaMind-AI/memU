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
    """Concise conversation memory management API"""

    def __init__(
        self, agent_id: str, user_id: str, data_dir: str = "data", db_manager=None
    ):
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

        # Create data directory (backward compatibility)
        os.makedirs(data_dir, exist_ok=True)

        # Use database manager
        if db_manager is not None:
            self.manager = ConversationManager(db_manager=db_manager)
        else:
            # Use global database manager (PostgreSQL)
            db_manager = get_database_manager()
            self.manager = ConversationManager(db_manager=db_manager)

    def add_conversation(
        self, user_message: str, ai_response: str, metadata: dict = None
    ):
        """Add conversation"""
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response},
        ]
        return self.manager.record_conversation(
            agent_id=self.agent_id,
            user_id=self.user_id,
            messages=messages,
            pipeline_result=metadata,  # metadata passed as pipeline_result
        )

    def search_similar_conversations(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.6
    ):
        """Search similar conversations"""
        return self.manager.search_similar_conversations(
            agent_id=self.agent_id,
            query=query,
            limit=top_k,
            similarity_threshold=similarity_threshold,
        )

    @property
    def conversations(self):
        """Get all conversations"""
        return self.manager.get_conversation_history(
            agent_id=self.agent_id, user_id=self.user_id
        )

    def close(self):
        """Close resources"""
        if hasattr(self.manager, "close"):
            self.manager.close()


__all__ = [
    "ConversationManager",
    "Conversation",
    "ConversationMessage",
    "Memo",  # New concise API
]
