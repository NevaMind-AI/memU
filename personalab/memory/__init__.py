"""
PersonaLab Memory Module

新的统一Memory架构，基于STRUCTURE.md设计：
- Memory: 统一的记忆管理类
- MemoryManager: Memory管理器
- MemoryUpdatePipeline: Memory更新Pipeline
- MemoryRepository: 数据库存储层

向后兼容的原有类：
- BaseMemory: 抽象基类（保持向后兼容）
- ProfileMemory: 画像记忆（现在作为组件）
- EventMemory: 事件记忆（现在作为组件）
"""

# 新的统一Memory架构
from .base import Memory, ProfileMemory, EventMemory
from .manager import MemoryManager, ConversationMemoryInterface
from .pipeline import MemoryUpdatePipeline, PipelineResult
from .storage import MemoryRepository

# 向后兼容的原有类
from .base import BaseMemory
from .profile import ProfileMemory as LegacyProfileMemory
from .events import EventMemory as LegacyEventMemory

__all__ = [
    # 新架构的主要类
    'Memory',
    'MemoryManager', 
    'ConversationMemoryInterface',
    'MemoryUpdatePipeline',
    'MemoryRepository',
    'PipelineResult',
    
    # Memory组件
    'ProfileMemory',
    'EventMemory',
    
    # 向后兼容类
    'BaseMemory',
    'LegacyProfileMemory',
    'LegacyEventMemory',
] 