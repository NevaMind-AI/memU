"""
PersonaLab Memory Module

Core Memory system including:
- Memory: Unified memory management class
- MemoryClient: Memory client for core memory operations
- MemoryUpdatePipeline: Memory update pipeline
- MemoryDB: Database storage layer
- EmbeddingManager: Vector embeddings (for backward compatibility)

Note: Conversation recording and vectorization are now handled by the memo module.

Backward compatible classes:
- BaseMemory: Abstract base class (for backward compatibility)
- ProfileMemory: Profile memory (now as component)
- EventMemory: Event memory (now as component)
"""

# 新的统一Memory架构
from .base import Memory, ProfileMemory, EventMemory, ToMMemory
from .manager import MemoryClient
from .pipeline import MemoryUpdatePipeline, PipelineResult, UpdateResult, ToMResult
from .storage import MemoryDB
# Embeddings moved to memo module

# LLM接口
from ..llm import BaseLLMClient

# 向后兼容的原有类（如果存在的话）
try:
    from .base import BaseMemory
except ImportError:
    BaseMemory = None

# 向后兼容别名
MemoryManager = MemoryClient

__all__ = [
    # 新架构的主要类
    'Memory',
    'MemoryClient', 
    'MemoryUpdatePipeline',
    'MemoryDB',
    'PipelineResult',
    'UpdateResult', 
    'ToMResult',

    
    # LLM接口
    'BaseLLMClient',
    
    # Memory组件
    'ProfileMemory',
    'EventMemory',
    'ToMMemory',
    
    # 向后兼容类和别名
    'BaseMemory',
    'MemoryManager',
] 