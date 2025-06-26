"""
OpenAI LLM implementation for PersonaLab.

This module provides integration with OpenAI's GPT models.
"""

import os
from typing import Any, Dict, Optional

try:
    import openai
except ImportError:
    openai = None

from .base import BaseLLM, LLMResponse


class OpenAILLM(BaseLLM):
    """OpenAI GPT implementation of the LLM interface."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: Optional[str] = None, **kwargs):
        """
        Initialize OpenAI LLM.
        
        Args:
            model_name: OpenAI model name (e.g., 'gpt-3.5-turbo', 'gpt-4')
            api_key: OpenAI API key (if not provided, will use OPENAI_API_KEY env var)
            **kwargs: Additional OpenAI client configuration
        """
        if openai is None:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        
        super().__init__(model_name, **kwargs)
        
        # Set up API key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key, **kwargs)
    
    def _get_provider_name(self) -> str:
        """Return the provider name."""
        return "OpenAI"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using OpenAI's API.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare API parameters
        api_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens
        
        # Make API call with timing
        response, response_time = self._measure_time(
            self.client.chat.completions.create,
            **api_params
        )
        
        # Extract response content
        content = response.choices[0].message.content
        
        # Prepare usage information
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        # Prepare metadata
        metadata = {
            "finish_reason": response.choices[0].finish_reason,
            "response_id": response.id,
            "created": response.created,
            "system_fingerprint": getattr(response, 'system_fingerprint', None)
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
            **kwargs: Additional OpenAI API parameters
            
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
        """List available OpenAI models."""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data if "gpt" in model.id]
        except Exception as e:
            print(f"Error fetching models: {e}")
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"]
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available and working."""
        try:
            # Simple test call
            test_response = self.generate("Hello", max_tokens=5)
            return test_response.content is not None
        except Exception:
            return False 