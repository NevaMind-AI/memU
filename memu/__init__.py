"""
MemU

A Python framework for creating and managing AI agent memories through file-based storage.

Refactored to use simplified file-based memory architecture with agent tools.
"""

__version__ = "0.1.3"
__author__ = "MemU Team"
__email__ = "support@personalab.ai"

# Configuration module - import from original config.py file
import importlib.util
import os

# LLM system
from .llm import AnthropicClient  # Anthropic implementation
from .llm import BaseLLMClient  # Base LLM client
from .llm import CustomLLMClient  # Custom LLM support
from .llm import LLMResponse  # LLM response object
from .llm import OpenAIClient  # OpenAI implementation

# Core Memory system - Hybrid storage (file + database)
from .memory import ProfileMemory, EventMemory  
from .memory.base import Memory, ProfileMemory, EventMemory, ReminderMemory, ImportantEventMemory, InterestsMemory, StudyMemory 
from .memory import MemoryAgent 
from .memory import MemoryFileManager 
from .memory import MemoryDatabaseManager 
from .memory import EmbeddingClient
from .memory import create_embedding_client  
from .memory import get_default_embedding_client 

# Prompts system
from .prompts import PromptLoader  # Prompt loading utilities
from .prompts import get_prompt_loader  # Get prompt loader instance

_config_file_path = os.path.join(os.path.dirname(__file__), "config.py")
_config_spec = importlib.util.spec_from_file_location(
    "personalab_config", _config_file_path
)
_config_module = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(_config_module)
config = _config_module.config
load_config = _config_module.load_config
setup_env_file = _config_module.setup_env_file
LLMConfigManager = _config_module.LLMConfigManager
get_llm_config_manager = _config_module.get_llm_config_manager

# Database configuration (optional - for backward compatibility)
from .config import (
    DatabaseConfig,
    DatabaseManager,
    get_database_manager,
    setup_postgresql,
)

# Backward compatibility (DEPRECATED - will be removed in future versions)
try:
    # Check if legacy components are available
    # Note: Currently no legacy components need to be imported
    # This is preserved for future backward compatibility needs
    _backward_compatibility_available = True
except ImportError:
    _backward_compatibility_available = False
    import warnings

    warnings.warn(
        "Some legacy components are not available. Please update to use the new Memory Agent API.",
        DeprecationWarning,
        stacklevel=2,
    )

__all__ = [
    # Core Memory system
    "Memory",  # Simple file-based Memory class
    "MemoryAgent",  # Agent-based memory management with LLM tools
    "MemoryFileManager",  # File operations for memory storage
    "MemoryDatabaseManager",  # Database operations with PostgreSQL + pgvector
    # Memory components
    "ProfileMemory",  # Profile memory component
    "EventMemory",  # Event memory component
    "ReminderMemory",  # Reminder memory component
    "ImportantEventMemory",  # Important event memory component
    "InterestsMemory",  # Interests memory component
    "StudyMemory",  # Study memory component
    # Embedding support
    "EmbeddingClient",  # Vector embedding client
    "create_embedding_client",  # Embedding client factory
    "get_default_embedding_client",  # Default embedding client getter
    # LLM system
    "BaseLLMClient",  # Base LLM client
    "LLMResponse",  # LLM response object
    "OpenAIClient",  # OpenAI implementation
    "AnthropicClient",  # Anthropic implementation
    "CustomLLMClient",  # Custom LLM support
    # Prompts system
    "PromptLoader",  # Prompt loading utilities
    "get_prompt_loader",  # Get prompt loader instance
    # Configuration
    "config",  # Global config instance
    "load_config",  # Config loader
    "setup_env_file",  # Environment setup helper
    "LLMConfigManager",  # Unified LLM config manager
    "get_llm_config_manager",  # Global LLM config getter
    # Database configuration (optional)
    "setup_postgresql",  # PostgreSQL setup
    "get_database_manager",  # Global database manager
    "DatabaseManager",  # Database manager class
    "DatabaseConfig",  # Database config class
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
            stacklevel=2,
        )
        from . import llm

        return llm
    
    if name in ["Persona", "ConversationManager", "MemoryClient", "MindMemory"]:
        import warnings
        warnings.warn(
            f"'{name}' has been removed. Please use the new MemoryAgent-based API.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise AttributeError(f"'{name}' is no longer available. Use MemoryAgent instead.")

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
