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
    MindMemory,                # Mind memory component
)

# Conversation management
from .memo import ConversationManager

# LLM system
from .llm import (
    BaseLLMClient,             # Base LLM client
    LLMResponse,               # LLM response object
    OpenAIClient,              # OpenAI implementation
    AnthropicClient,           # Anthropic implementation  
    CustomLLMClient,           # Custom LLM support
)

# Persona API - Simple entry point
from .persona import Persona

# Configuration module
from .config import config, load_config, setup_env_file, LLMConfigManager, get_llm_config_manager

# Backward compatibility (DEPRECATED - will be removed in future versions)
try:
    from .memory import BaseMemory
    _backward_compatibility_available = True
except ImportError:
    _backward_compatibility_available = False
    import warnings
    warnings.warn(
        "Some legacy components are not available. Please update to use the new Memory API.",
        DeprecationWarning,
        stacklevel=2
    )

__all__ = [
    # Main API
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
    "MindMemory",                # Mind memory component
    
    # Conversation management
    "ConversationManager",       # Conversation recording and search
    
    # LLM system
    "BaseLLMClient",             # Base LLM client
    "LLMResponse",               # LLM response object
    "OpenAIClient",              # OpenAI implementation
    "AnthropicClient",           # Anthropic implementation
    "CustomLLMClient",           # Custom LLM support
    
    # Configuration
    "config",                    # Global config instance
    "load_config",               # Config loader
    "setup_env_file",            # Environment setup helper
    "LLMConfigManager",          # Unified LLM config manager
    "get_llm_config_manager",    # Global LLM config getter
]

# Legacy support (conditional export)
if _backward_compatibility_available:
    __all__.append("BaseMemory")

# Deprecation warning for legacy imports
def __getattr__(name):
    """Handle legacy imports with deprecation warnings"""
    if name == "llm":
        import warnings
        warnings.warn(
            "Direct 'llm' module import is deprecated. Use specific LLM client imports instead.",
            DeprecationWarning,
            stacklevel=2
        )
        from . import llm
        return llm
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 