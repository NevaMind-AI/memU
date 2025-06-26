"""
Anthropic Claude LLM implementation for PersonaLab.

This module provides integration with Anthropic's Claude models.
"""

import os
from typing import Any, Dict, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

from .base import BaseLLM, LLMResponse


class AnthropicLLM(BaseLLM):
    """Anthropic Claude implementation of the LLM interface."""
    
    def __init__(self, model_name: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None, **kwargs):
        """
        Initialize Anthropic LLM.
        
        Args:
            model_name: Anthropic model name (e.g., 'claude-3-sonnet-20240229', 'claude-3-opus-20240229')
            api_key: Anthropic API key (if not provided, will use ANTHROPIC_API_KEY env var)
            **kwargs: Additional Anthropic client configuration
        """
        if anthropic is None:
            raise ImportError("Anthropic package not installed. Install with: pip install anthropic")
        
        super().__init__(model_name, **kwargs)
        
        # Set up API key
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key, **kwargs)
    
    def _get_provider_name(self) -> str:
        """Return the provider name."""
        return "Anthropic"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using Anthropic's API.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic API parameters
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        # Prepare API parameters
        api_params = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens or 1024,
            **kwargs
        }
        
        if system_prompt:
            api_params["system"] = system_prompt
        
        # Make API call with timing
        response, response_time = self._measure_time(
            self.client.messages.create,
            **api_params
        )
        
        # Extract response content
        content = ""
        if response.content and len(response.content) > 0:
            content = response.content[0].text
        
        # Prepare usage information
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        
        # Prepare metadata
        metadata = {
            "stop_reason": response.stop_reason,
            "stop_sequence": response.stop_sequence,
            "response_id": response.id,
            "type": response.type,
            "role": response.role
        }
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            provider=self.provider_name,
            usage=usage,
            response_time=response_time,
            metadata=metadata
        )
    
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
            **kwargs: Additional Anthropic API parameters
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        # Format memory context
        memory_text = self._format_memory_context(memory_context)
        
        # Enhance system prompt with memory context
        enhanced_system_prompt = system_prompt or ""
        if memory_text:
            enhanced_system_prompt += f"\n\nRELEVANT MEMORY CONTEXT:\n{memory_text}"
        
        return self.generate(
            prompt=prompt,
            system_prompt=enhanced_system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def list_available_models(self) -> list:
        """List available Anthropic models."""
        # Anthropic doesn't provide a dynamic model list API, so we return known models
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    def is_available(self) -> bool:
        """Check if Anthropic API is available and working."""
        try:
            # Simple test call
            test_response = self.generate("Hello", max_tokens=5)
            return test_response.content is not None
        except Exception:
            return False 