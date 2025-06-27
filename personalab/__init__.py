"""
PersonaLab

A Python framework for creating and managing AI personas and laboratory environments.

新版本基于STRUCTURE.md重构，采用统一的Memory架构。
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# 新的统一Memory架构
from .memory import (
    Memory,                    # 统一Memory类
    MemoryManager,             # Memory管理器
    ConversationMemoryInterface,  # 对话Memory接口
    MemoryUpdatePipeline,      # Memory更新Pipeline
    MemoryRepository,          # 数据库存储层
    PipelineResult,            # Pipeline结果
    
    # Memory组件
    ProfileMemory,             # 画像记忆组件
    EventMemory,               # 事件记忆组件
    ToMMemory,                 # Theory of Mind记忆组件
    
    # 向后兼容
    BaseMemory,                # 保持向后兼容的基类
    LegacyProfileMemory,       # 原有的ProfileMemory
    LegacyEventMemory,         # 原有的EventMemory
)

# LLM module
from . import llm
from .llm import BaseLLMClient, OpenAIClient, create_llm_client

# Configuration module
from .config import config, load_config, setup_env_file

__all__ = [
    # 新Memory架构 - 主要接口
    "Memory",                    # 统一Memory类
    "MemoryManager",             # Memory管理器
    "ConversationMemoryInterface",  # 对话Memory接口
    "MemoryUpdatePipeline",      # Memory更新Pipeline
    "MemoryRepository",          # 数据库存储层
    "PipelineResult",            # Pipeline结果
    
    # Memory组件
    "ProfileMemory",             # 画像记忆组件
    "EventMemory",               # 事件记忆组件
    "ToMMemory",                 # Theory of Mind记忆组件
    
    # 向后兼容
    "BaseMemory",                # 保持向后兼容的基类
    "LegacyProfileMemory",       # 原有的ProfileMemory
    "LegacyEventMemory",         # 原有的EventMemory
    
    # LLM system
    "llm", "BaseLLMClient", "OpenAIClient", "create_llm_client",
    
    # Configuration
    "config", "load_config", "setup_env_file"
] 