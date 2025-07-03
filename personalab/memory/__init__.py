"""
PersonaLab Memory Module

Core Memory system including:
- Memory: Unified memory management class
- MemoryClient: Memory client for core memory operations
- MemoryUpdatePipeline: Memory update pipeline

Note: Only PostgreSQL with pgvector is supported.
Conversation recording and vectorization are handled by the memo module.

Backward compatible classes:
- BaseMemory: Abstract base class (for backward compatibility)
- ProfileMemory: Profile memory (now as component)
- EventMemory: Event memory (now as component)
"""

# LLM interface
from ..llm import BaseLLMClient

# New unified Memory architecture
from .base import EventMemory, Memory, MindMemory, ProfileMemory
from .manager import MemoryClient
from .pipeline import MemoryUpdatePipeline, MindResult, PipelineResult, UpdateResult

# Embeddings moved to memo module


# Backward compatible legacy classes (if they exist)
try:
    from .base import BaseMemory
except ImportError:
    BaseMemory = None

# Backward compatible aliases
MemoryManager = MemoryClient

__all__ = [
    # Main classes of new architecture
    "Memory",
    "MemoryClient",
    "MemoryUpdatePipeline",
    "PipelineResult",
    "UpdateResult",
    "MindResult",
    # LLM interface
    "BaseLLMClient",
    # Memory components
    "ProfileMemory",
    "EventMemory",
    "MindMemory",
    # Backward compatible classes and aliases
    "BaseMemory",
    "MemoryManager",
]
