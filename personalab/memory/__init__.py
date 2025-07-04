"""
PersonaLab Memory Module

Core Memory system with API-based remote operations:
- Memory: Unified API-based memory management class
- MemoryClient: API client for remote memory operations
- Memory component classes: ProfileMemory, EventMemory, MindMemory

Architecture: Client -> API -> Backend -> Database
All memory operations are performed through remote API calls for consistent
and scalable memory management.

Note: Only API-based memory operations are supported.
The Memory class internally uses ProfileMemory, EventMemory, and MindMemory 
components for code organization while all data operations go through remote API.
"""

# Main Memory classes
from .base import Memory, ProfileMemory, EventMemory, MindMemory
from .manager import MemoryClient

# LLM interface
from ..llm import BaseLLMClient

__all__ = [
    # Main classes
    "Memory",
    "MemoryClient", 
    # Memory components
    "ProfileMemory",
    "EventMemory", 
    "MindMemory",
    # LLM interface
    "BaseLLMClient",
]
