"""
MemU Memory Module - Function Calling Architecture

Modern memory system with function calling interface:

CORE ARCHITECTURE:
- MemoryAgent: Function calling interface for LLM agents (main interface)
- RecallAgent: File system operations and content retrieval

STORAGE:
- MemoryFileManager: File operations for memory storage (.md files)
- EmbeddingClient: Vector embedding generation for semantic search

WORKFLOW:
1. LLM Agent → Function Calling → Memory Operations → Markdown Files
2. Memory stored with embeddings for semantic retrieval (per-line basis)
3. RecallAgent provides file system scanning and content search capabilities
4. All memory operations exposed as standardized function calls
"""

from .embeddings import get_default_embedding_client
from .file_manager import MemoryFileManager
from .memory_agent import MemoryAgent
from .recall_agent import RecallAgent

__all__ = [
    "MemoryAgent",  # Function calling interface
    "RecallAgent",
    "MemoryFileManager",
    "get_default_embedding_client",
]
