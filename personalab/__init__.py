"""
PersonaLab

A Python framework for creating and managing AI personas and laboratory environments.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Memory system - now using modular structure
from .memory import (
    BaseMemory,               # Base class
    ProfileMemory,            # Profile storage
    EventMemory,              # Event storage
    UserMemory,               # User memory container
    AgentMemory               # Agent memory container
)
from .main import Memory      # Main memory manager

# LLM module (optional imports with error handling)
try:
    from . import llm
    from .llm import LLMManager, BaseLLM, LLMResponse
    _llm_available = True
except ImportError:
    llm = None
    LLMManager = None
    BaseLLM = None
    LLMResponse = None
    _llm_available = False

__all__ = [
    # Memory system - modular structure
    "Memory",                    # Main memory manager
    "BaseMemory",               # Base class
    "ProfileMemory",            # Profile storage
    "EventMemory",              # Event storage  
    "UserMemory",               # User memory container
    "AgentMemory",              # Agent memory container
    # LLM system (if available)
    "llm", "LLMManager", "BaseLLM", "LLMResponse"
]

# Remove None values from __all__ if LLM not available
if not _llm_available:
    __all__ = [item for item in __all__ if not item.startswith(('llm', 'LLM', 'BaseLLM'))] 