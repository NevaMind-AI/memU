"""
MemU

A Python framework for creating and managing AI agent memories through file-based storage.

Simplified unified memory architecture with a single Memory Agent.
"""

__version__ = "0.2.1"
__author__ = "MemU Team"
__email__ = "support@nevamind.ai"

# Configuration module

# LLM system
from .llm import BaseLLMClient  # Base LLM client
from .llm import CustomLLMClient  # Custom LLM support
from .llm import LLMResponse  # LLM response object
from .llm import OpenAIClient  # OpenAI implementation

# Core Memory system - Unified Memory Agent
from .memory import MemoryAgent  # Unified memory agent
from .memory import MemoryFileManager, get_default_embedding_client

# SDK system - HTTP client for MemU API services
from .sdk.python import MemorizeRequest, MemorizeResponse, MemuClient

# Prompts system - now reads from dynamic configuration folders
# from .config.prompts import PromptLoader  # Prompt loading utilities
# from .config.prompts import get_prompt_loader  # Get prompt loader instance

# Note: legacy `memu/config.py` has been removed. Server configuration now
# lives under `memu/server/config.py`. Markdown configuration lives under
# `memu/config/markdown_config.py`.

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
    # "AnthropicClient",  # Anthropic implementation
    "CustomLLMClient",  # Custom LLM support
    "OpenRouterClient"  # OpenRouter support
    # SDK system - HTTP client for MemU API services
    "MemuClient",  # HTTP client for MemU API
    "MemorizeRequest",  # Request model for memorize API
    "MemorizeResponse",  # Response model for memorize API
    # Prompts system - now reads from dynamic configuration folders
    # "PromptLoader",  # Prompt loading utilities
    # "get_prompt_loader",  # Get prompt loader instance
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
