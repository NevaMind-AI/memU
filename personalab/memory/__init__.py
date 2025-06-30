"""
PersonaLab Memory Module

统一Memory架构，包含：
- Memory: 统一的记忆管理类
- MemoryClient: Memory客户端，支持conversation记录和向量化
- MemoryUpdatePipeline: Memory更新Pipeline
- MemoryDB: 数据库存储层
- EmbeddingManager: 向量化和语义搜索功能

向后兼容的原有类：
- BaseMemory: 抽象基类（保持向后兼容）
- ProfileMemory: 画像记忆（现在作为组件）
- EventMemory: 事件记忆（现在作为组件）
"""

# 新的统一Memory架构
from .base import Memory, ProfileMemory, EventMemory, ToMMemory
from .manager import MemoryClient
from .pipeline import MemoryUpdatePipeline, PipelineResult, UpdateResult, ToMResult
from .storage import MemoryDB
from .embeddings import EmbeddingManager, create_embedding_manager

# LLM接口
from ..llm import BaseLLMClient, create_llm_client

# 向后兼容的原有类（如果存在的话）
try:
    from .base import BaseMemory
except ImportError:
    BaseMemory = None

# 向后兼容别名
MemoryManager = MemoryClient
MemoryRepository = MemoryDB  # 向后兼容别名

__all__ = [
    # 新架构的主要类
    'Memory',
    'MemoryClient', 
    'MemoryUpdatePipeline',
    'MemoryDB',
    'PipelineResult',
    'UpdateResult', 
    'ToMResult',
    
    # 向量化和搜索功能
    'EmbeddingManager',
    'create_embedding_manager',
    
    # LLM接口
    'BaseLLMClient',
    'create_llm_client',
    
    # Memory组件
    'ProfileMemory',
    'EventMemory',
    'ToMMemory',
    
    # 向后兼容类和别名
    'BaseMemory',
    'MemoryManager',
    'MemoryRepository',
] 