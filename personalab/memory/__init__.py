"""
PersonaLab Memory Module

新的统一Memory架构，基于STRUCTURE.md设计：
- Memory: 统一的记忆管理类
- MemoryClient: Memory客户端
- MemoryUpdatePipeline: Memory更新Pipeline
- MemoryRepository: 数据库存储层

向后兼容的原有类：
- BaseMemory: 抽象基类（保持向后兼容）
- ProfileMemory: 画像记忆（现在作为组件）
- EventMemory: 事件记忆（现在作为组件）
"""

# 新的统一Memory架构
from .base import Memory, ProfileMemory, EventMemory, ToMMemory
from .manager import MemoryClient, ConversationMemoryInterface
from .pipeline import MemoryUpdatePipeline, PipelineResult, UpdateResult, ToMResult
from ..llm import BaseLLMClient, OpenAIClient, create_llm_client
from .storage import MemoryRepository

# 向后兼容的原有类
from .base import BaseMemory
from .profile import ProfileMemory as LegacyProfileMemory
from .events import EventMemory as LegacyEventMemory

# 向后兼容别名
MemoryManager = MemoryClient

__all__ = [
    # 新架构的主要类
    'Memory',
    'MemoryClient', 
    'ConversationMemoryInterface',
    'MemoryUpdatePipeline',
    'MemoryRepository',
    'PipelineResult',

    'UpdateResult', 
    'ToMResult',
    
        # LLM接口
    'BaseLLMClient',
    'OpenAIClient',
    'create_llm_client',
    
    # Memory组件
    'ProfileMemory',
    'EventMemory',
    'ToMMemory',
    
    # 向后兼容类
    'BaseMemory',
    'LegacyProfileMemory',
    'LegacyEventMemory',
    'MemoryManager',  # 向后兼容别名
] 