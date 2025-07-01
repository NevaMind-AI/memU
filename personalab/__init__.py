"""
PersonaLab

A Python framework for creating and managing AI personas and laboratory environments.

新版本基于STRUCTURE.md重构，采用统一的Memory架构。
"""

__version__ = "0.1.0"
__author__ = "PersonaLab Team"
__email__ = "support@personalab.ai"

# Core Memory system
from .memory import (
    Memory,                    # Unified Memory class
    MemoryClient,              # Memory client
    MemoryUpdatePipeline,      # Memory update pipeline
    MemoryDB,                  # Database storage layer
    PipelineResult,            # Pipeline result
    
    # Memory components
    ProfileMemory,             # Profile memory component
    EventMemory,               # Event memory component
    ToMMemory,                 # Theory of Mind memory component
    
    # Backward compatibility
    BaseMemory,                # Backward compatible base class
)

# Conversation management
from .memo import ConversationManager

# LLM system - NEW!
from .llm import (
    BaseLLMClient,             # Base LLM client
    LLMResponse,               # LLM response object
    OpenAIClient,              # OpenAI implementation
    AnthropicClient,           # Anthropic implementation  
    CustomLLMClient,           # Custom LLM support
)

# Persona API - Simple entry point
from .persona import Persona

# Legacy LLM module (for backward compatibility)
from . import llm

# Configuration module
from .config import config, load_config, setup_env_file

__all__ = [
    # Simple API
    "Persona",                   # Main entry point - simple API
    
    # Core Memory system
    "Memory",                    # Unified Memory class
    "MemoryClient",              # Memory client
    "MemoryUpdatePipeline",      # Memory update pipeline
    "MemoryDB",                  # Database storage layer
    "PipelineResult",            # Pipeline result
    
    # Memory components
    "ProfileMemory",             # Profile memory component
    "EventMemory",               # Event memory component
    "ToMMemory",                 # Theory of Mind memory component
    
    # Backward compatibility
    "BaseMemory",                # Backward compatible base class
    
    # Conversation management
    "ConversationManager",       # Conversation recording and search
    
    # LLM system
    "BaseLLMClient",             # Base LLM client
    "LLMResponse",               # LLM response object
    "OpenAIClient",              # OpenAI implementation
    "AnthropicClient",           # Anthropic implementation
    "CustomLLMClient",           # Custom LLM support
    
    # Legacy
    "llm",                       # LLM module
    
    # Configuration
    "config", "load_config", "setup_env_file",
] 