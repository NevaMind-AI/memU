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

# Persona API - Simple entry point
from .persona import Persona

# LLM module
from . import llm
from .llm import BaseLLMClient, OpenAIClient, create_llm_client

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
    "llm", "BaseLLMClient", "OpenAI", "create_llm_client",
    
    # Configuration
    "config", "load_config", "setup_env_file",
] 