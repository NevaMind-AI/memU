"""
MemU Memory Module - Clean Two-Agent Architecture

Simplified memory system with specialized agents:

CORE ARCHITECTURE:
- MemoryAgent: LLM-based conversation processing with session splitting
- RecallAgent: File system operations and content retrieval

STORAGE:
- MemoryFileManager: File operations for memory storage (.md files)
- EmbeddingClient: Vector embedding generation for semantic search

WORKFLOW:
1. Conversation → LLM Session Splitting → Session Embeddings → Memory Types
2. Memory stored as markdown files with embeddings for semantic retrieval
3. RecallAgent provides file system scanning and content search capabilities
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
