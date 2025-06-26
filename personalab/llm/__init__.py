"""
PersonaLab LLM Module

This module provides a unified interface for different LLM providers,
allowing easy switching between OpenAI, Anthropic, Google, Azure, AWS Bedrock,
Cohere, Together AI, Replicate, local models, and more.
"""

from .base import BaseLLM, LLMResponse
from .openai_llm import OpenAILLM
from .anthropic_llm import AnthropicLLM
from .local_llm import LocalLLM
from .manager import LLMManager

# New LLM providers (with optional imports)
try:
    from .google_llm import GoogleLLM
except ImportError:
    GoogleLLM = None

try:
    from .azure_openai_llm import AzureOpenAILLM
except ImportError:
    AzureOpenAILLM = None

try:
    from .cohere_llm import CohereLLM
except ImportError:
    CohereLLM = None

try:
    from .bedrock_llm import BedrockLLM
except ImportError:
    BedrockLLM = None

try:
    from .together_llm import TogetherLLM
except ImportError:
    TogetherLLM = None

try:
    from .replicate_llm import ReplicateLLM
except ImportError:
    ReplicateLLM = None

__all__ = [
    # Core classes
    "BaseLLM",
    "LLMResponse", 
    "LLMManager",
    
    # Original providers
    "OpenAILLM",
    "AnthropicLLM", 
    "LocalLLM",
    
    # New providers (may be None if dependencies not installed)
    "GoogleLLM",
    "AzureOpenAILLM",
    "CohereLLM",
    "BedrockLLM",
    "TogetherLLM",
    "ReplicateLLM"
]

# Remove None values from __all__ if dependencies are missing
__all__ = [item for item in __all__ if globals().get(item) is not None] 