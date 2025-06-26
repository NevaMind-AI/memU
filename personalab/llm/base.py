"""
Base LLM interface for PersonaLab.

This module defines the abstract base class that all LLM implementations must inherit from,
ensuring a consistent interface across different providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import time


@dataclass
class LLMResponse:
    """Standard response format for all LLM providers."""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, Any]] = None
    response_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class BaseLLM(ABC):
    """
    Abstract base class for all LLM implementations.
    
    This class defines the interface that all LLM providers must implement,
    ensuring consistent behavior across different providers.
    """
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the LLM with a specific model.
        
        Args:
            model_name: Name of the model to use
            **kwargs: Provider-specific configuration options
        """
        self.model_name = model_name
        self.config = kwargs
        self.provider_name = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        """Return the name of the LLM provider."""
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        pass
    
    @abstractmethod
    def generate_with_memory(
        self,
        prompt: str,
        memory_context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using memory context.
        
        Args:
            prompt: The user prompt/message
            memory_context: Memory search results to include as context
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        pass
    
    def _format_memory_context(self, memory_context: Dict[str, Any]) -> str:
        """
        Format memory search results into a readable context string.
        
        Args:
            memory_context: Memory search results from Memory.search_memory_with_context()
            
        Returns:
            Formatted context string for the LLM
        """
        if not memory_context or memory_context.get("total_matches", 0) == 0:
            return ""
        
        context_parts = []
        
        # Add agent profile information
        if memory_context.get("agent_profile_matches"):
            context_parts.append("AGENT PROFILE:")
            for match in memory_context["agent_profile_matches"]:
                context_parts.append(f"- {match['content']}")
        
        # Add relevant agent events
        if memory_context.get("agent_event_matches"):
            context_parts.append("\nRELEVANT AGENT MEMORIES:")
            for match in memory_context["agent_event_matches"][:3]:  # Limit to top 3
                context_parts.append(f"- {match['content']}")
        
        # Add user profile information
        if memory_context.get("user_profile_matches"):
            context_parts.append("\nUSER PROFILE:")
            for match in memory_context["user_profile_matches"]:
                context_parts.append(f"- User {match['user_id']}: {match['content']}")
        
        # Add relevant user events
        if memory_context.get("user_event_matches"):
            context_parts.append("\nRELEVANT USER MEMORIES:")
            for match in memory_context["user_event_matches"][:5]:  # Limit to top 5
                context_parts.append(f"- User {match['user_id']}: {match['content']}")
        
        return "\n".join(context_parts)
    
    def _measure_time(self, func, *args, **kwargs):
        """Helper method to measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    def is_available(self) -> bool:
        """
        Check if the LLM provider is available and properly configured.
        
        Returns:
            True if the provider is ready to use, False otherwise
        """
        try:
            # Simple test to check if the provider is working
            test_response = self.generate("Hello", max_tokens=5)
            return test_response.content is not None
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary containing model information
        """
        return {
            "model_name": self.model_name,
            "provider": self.provider_name,
            "config": self.config
        }
    
    def __str__(self) -> str:
        return f"{self.provider_name}({self.model_name})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.model_name}>" 