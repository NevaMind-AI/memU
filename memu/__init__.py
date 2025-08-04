"""
MemU

A Python framework for creating and managing AI agent memories through file-based storage.

Simplified unified memory architecture with a single Memory Agent.
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

# Core Memory system - Unified Memory Agent
from .memory import MemoryAgent  # Unified memory agent
from .memory import MemoryFileManager, get_default_embedding_client

# SDK system - HTTP client for MemU API services
from .sdk import MemorizeRequest, MemorizeResponse, MemuClient

# Prompts system - now reads from dynamic configuration folders
# from .config.prompts import PromptLoader  # Prompt loading utilities
# from .config.prompts import get_prompt_loader  # Get prompt loader instance

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

# Note: Database functionality has been removed.
# MemU now uses file-based storage only.

__all__ = [
    # Core Memory system
    "Memory",  # Simple file-based Memory class
    "MemoryAgent",  # Unified memory agent
    "MemoryFileManager",  # File operations for memory storage
    # Memory components
    "ProfileMemory",  # Profile memory component
    "EventMemory",  # Event memory component
    "ReminderMemory",  # Reminder memory component
    "ImportantEventMemory",  # Important event memory component
    "InterestsMemory",  # Interests memory component
    "StudyMemory",  # Study memory component
    # Embedding support
    "EmbeddingClient",  # Vector embedding client
    "create_embedding_client",
    "get_default_embedding_client",  # Default embedding client getter
    # LLM system
    "BaseLLMClient",  # Base LLM client
    "LLMResponse",  # LLM response object
    "OpenAIClient",  # OpenAI implementation
    "AnthropicClient",  # Anthropic implementation
    "CustomLLMClient",  # Custom LLM support
    # SDK system - HTTP client for MemU API services
    "MemuClient",  # HTTP client for MemU API
    "MemorizeRequest",  # Request model for memorize API
    "MemorizeResponse",  # Response model for memorize API
    # Prompts system - now reads from dynamic configuration folders
    # "PromptLoader",  # Prompt loading utilities
    # "get_prompt_loader",  # Get prompt loader instance
    # Configuration
    "config",  # Global config instance
    "load_config",  # Config loader
    "setup_env_file",  # Environment setup helper
    "LLMConfigManager",  # Unified LLM config manager
    "get_llm_config_manager",  # Global LLM config getter
    # Note: Database functionality has been removed
    # MemU now uses file-based storage only
]


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

    if name in [
        "MetaAgent",
        "BaseAgent",
        "ActivityAgent",
        "ProfileAgent",
        "EventAgent",
        "ReminderAgent",
        "InterestAgent",
        "StudyAgent",
        "create_agent",
        "get_available_agents",
        "Persona",
        "ConversationManager",
        "MemoryClient",
        "MindMemory",
        "AgentRegistry",
        "AgentConfig",
    ]:
        import warnings

        warnings.warn(
            f"'{name}' has been removed. Please use the new MemoryAgent instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Return a dummy class to provide deprecation warning without breaking import
        class DeprecatedClass:
            def __init__(self, *args, **kwargs):
                warnings.warn(
                    f"'{name}' is deprecated. Use MemoryAgent instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                raise AttributeError(
                    f"'{name}' is no longer available. Use MemoryAgent instead."
                )

        return DeprecatedClass

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
