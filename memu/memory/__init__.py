"""
MemU Memory Module - Simplified Two-Agent Architecture

Simplified memory system with specialized agents:

CORE ARCHITECTURE:
- MemoryAgent: Core memory processing (conversation to memory, CRUD operations)
- RecallAgent: File system operations (import/export, document scanning, content retrieval)

STORAGE SUPPORT:
- MemoryFileManager: File operations for memory storage (.md files)
- EmbeddingClient: Vector embedding generation for semantic search

ARCHITECTURE FLOW:
1. MemoryAgent: Raw Conversation → Memory Types (activity.md, profile.md, events.md, etc.)
2. RecallAgent: Local Documents → Import to Memory, Search/Retrieve existing content
3. Both agents use dynamic config loading from memu/config/ folders

BENEFITS:
- Clear separation of concerns: Processing vs File Operations
- Simplified interfaces: Focused tool sets per agent
- Configuration-driven: Categories loaded from config folders
- Easier maintenance: Specialized responsibilities
"""

from .memory_agent import MemoryAgent
from .recall_agent import RecallAgent
from .file_manager import MemoryFileManager
from .embeddings import get_default_embedding_client

__all__ = [
    "MemoryAgent",
    "RecallAgent", 
    "MemoryFileManager",
    "get_default_embedding_client"
]
