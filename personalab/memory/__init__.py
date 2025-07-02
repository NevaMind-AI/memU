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

# LLM接口
from ..llm import BaseLLMClient

# 新的统一Memory架构
from .base import EventMemory, Memory, MindMemory, ProfileMemory
from .manager import MemoryClient
from .pipeline import MemoryUpdatePipeline, PipelineResult, MindResult, UpdateResult

# Embeddings moved to memo module


# 向后兼容的原有类（如果存在的话）
try:
    from .base import BaseMemory
except ImportError:
    BaseMemory = None

# 向后兼容别名
MemoryManager = MemoryClient

__all__ = [
    # 新架构的主要类
    "Memory",
    "MemoryClient",
    "MemoryUpdatePipeline",
    "PipelineResult",
    "UpdateResult",
    "MindResult",
    # LLM接口
    "BaseLLMClient",
    # Memory组件
    "ProfileMemory",
    "EventMemory",
    "MindMemory",
    # 向后兼容类和别名
    "BaseMemory",
    "MemoryManager",
]
