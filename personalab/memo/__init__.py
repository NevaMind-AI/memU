"""
PersonaLab Memo Module

Conversation recording, storage, and retrieval functionality:
- ConversationDB: Database operations for conversation storage
- ConversationManager: High-level conversation management
- Integration with vector embeddings for semantic search
"""

from .storage import ConversationDB
from .manager import ConversationManager
from .models import Conversation, ConversationMessage

__all__ = [
    'ConversationDB',
    'ConversationManager', 
    'Conversation',
    'ConversationMessage',
] 