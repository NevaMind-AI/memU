"""
MemU

A Python framework for creating and managing AI personas and laboratory environments.

New version refactored based on STRUCTURE.md, adopting unified Memory architecture.
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

# Conversation management
from .memo import ConversationManager

# MemoryDB removed - using PostgreSQL storage only
# Core Memory system
from .memory import EventMemory  # Event memory component
from .memory import Memory  # Unified Memory class
from .memory import MemoryClient  # Memory client
# Note: MemoryUpdatePipeline is still used in backend server for memory processing
from .memory import MindMemory  # Mind memory component
# Note: PipelineResult is still used in backend server for memory processing
from .memory import ProfileMemory  # Memory components; Profile memory component

# Persona API - Simple entry point
from .persona import Persona

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

# Database configuration
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
        "Some legacy components are not available. Please update to use the new Memory API.",
        DeprecationWarning,
        stacklevel=2,
    )

__all__ = [
    # Main API
    "Persona",  # Main entry point - simple API
    # Core Memory system
    "Memory",  # Unified Memory class
    "MemoryClient",  # Memory client
    # Note: MemoryUpdatePipeline and PipelineResult are used in backend server but not exported in public API
    # Memory components
    "ProfileMemory",  # Profile memory component
    "EventMemory",  # Event memory component
    "MindMemory",  # Mind memory component
    # Conversation management
    "ConversationManager",  # Conversation recording and search
    # LLM system
    "BaseLLMClient",  # Base LLM client
    "LLMResponse",  # LLM response object
    "OpenAIClient",  # OpenAI implementation
    "AnthropicClient",  # Anthropic implementation
    "CustomLLMClient",  # Custom LLM support
    # Configuration
    "config",  # Global config instance
    "load_config",  # Config loader
    "setup_env_file",  # Environment setup helper
    "LLMConfigManager",  # Unified LLM config manager
    "get_llm_config_manager",  # Global LLM config getter
    # Database configuration
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

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
