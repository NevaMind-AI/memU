"""
MemU Memory Module

Hybrid memory system supporting both file-based and database storage:
- MemoryAgent: Agent-based memory management with LLM tools
- Memory: Simple file-based memory management class
- MemoryFileManager: File operations for memory storage
- MemoryDatabaseManager: Database operations with PostgreSQL + pgvector
- EmbeddingClient: Vector embedding generation for semantic search

Architecture: 
- File mode: Agent -> File Manager -> .md files
- Database mode: Agent -> Database Manager -> PostgreSQL + pgvector

The MemoryAgent provides LLM-powered tools for analyzing conversations
and updating character memories. In database mode, it supports vector
similarity search for enhanced memory retrieval.
"""

# Main Memory classes
from .base import Memory, ProfileMemory, EventMemory
from .agent import MemoryAgent
from .file_manager import MemoryFileManager
from .db_manager import MemoryDatabaseManager
from .embeddings import EmbeddingClient, create_embedding_client, get_default_embedding_client

# LLM interface
from ..llm import BaseLLMClient

__all__ = [
    # Main classes
    "Memory",
    "MemoryAgent",
    # Storage managers
    "MemoryFileManager", 
    "MemoryDatabaseManager",
    # Memory components
    "ProfileMemory",
    "EventMemory",
    # Embedding support
    "EmbeddingClient",
    "create_embedding_client", 
    "get_default_embedding_client",
    # LLM interface
    "BaseLLMClient",
]
