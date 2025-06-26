"""
Cohere LLM implementation for PersonaLab.

This module provides support for Cohere models through the Cohere API.
"""

import os
import time
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    cohere = None

from .base import BaseLLM, LLMResponse


class CohereLLM(BaseLLM):
    """
    Cohere LLM implementation.
    
    Supports Cohere models like:
    - command
    - command-light
    - command-nightly
    - command-r
    - command-r-plus
    """
    
    def __init__(self, 
                 model: str = "command",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 p: float = 1.0,
                 k: int = 0,
                 frequency_penalty: float = 0.0,
                 presence_penalty: float = 0.0,
                 **kwargs):
        """
        Initialize Cohere LLM.
        
        Args:
            model: Model name (e.g., 'command', 'command-r')
            api_key: Cohere API key (if not provided, uses COHERE_API_KEY env var)
            temperature: Sampling temperature (0.0 to 5.0)
            max_tokens: Maximum tokens to generate
            p: Nucleus sampling parameter (0.0 to 1.0)
            k: Top-k sampling parameter
            frequency_penalty: Frequency penalty (0.0 to 1.0)
            presence_penalty: Presence penalty (0.0 to 1.0)
            **kwargs: Additional model parameters
        """
        if not COHERE_AVAILABLE:
            raise ImportError(
                "Cohere library not available. Install with: "
                "pip install cohere"
            )
        
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        
        # Set up API key
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Cohere API key not provided. Set COHERE_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.p = p
        self.k = k
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.kwargs = kwargs
        
        # Initialize client
        self._client = cohere.Client(api_key=self.api_key)
    
    async def generate_async(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           memory_context: Optional[str] = None,
                           **kwargs) -> LLMResponse:
        """
        Generate response asynchronously using Cohere.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        start_time = time.time()
        
        try:
            # Construct full prompt
            full_prompt = self._construct_prompt(prompt, system_prompt, memory_context)
            
            # Prepare parameters
            params = {
                "model": self.model,
                "prompt": full_prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "p": kwargs.get("p", self.p),
                "k": kwargs.get("k", self.k) if kwargs.get("k", self.k) > 0 else None,
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty)
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make API call (Cohere doesn't have async client, so we'll simulate)
            response = self._client.generate(**params)
            
            # Extract response
            content = response.generations[0].text
            finish_reason = response.generations[0].finish_reason or "stop"
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="cohere",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason=finish_reason
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="cohere",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=end_time - start_time,
                finish_reason="error"
            )
    
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                memory_context: Optional[str] = None,
                **kwargs) -> LLMResponse:
        """
        Generate response synchronously using Cohere.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        start_time = time.time()
        
        try:
            # Construct full prompt
            full_prompt = self._construct_prompt(prompt, system_prompt, memory_context)
            
            # Prepare parameters
            params = {
                "model": self.model,
                "prompt": full_prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "p": kwargs.get("p", self.p),
                "k": kwargs.get("k", self.k) if kwargs.get("k", self.k) > 0 else None,
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty)
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make API call
            response = self._client.generate(**params)
            
            # Extract response
            content = response.generations[0].text
            finish_reason = response.generations[0].finish_reason or "stop"
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="cohere",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason=finish_reason
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="cohere",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=end_time - start_time,
                finish_reason="error"
            )
    
    async def stream_async(self, 
                          prompt: str, 
                          system_prompt: Optional[str] = None,
                          memory_context: Optional[str] = None,
                          **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream response asynchronously using Cohere.
        
        Note: Cohere's current API doesn't support streaming, so this simulates streaming
        by yielding the complete response.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Yields:
            Streaming text chunks
        """
        try:
            # Generate complete response
            response = await self.generate_async(prompt, system_prompt, memory_context, **kwargs)
            
            # Simulate streaming by yielding chunks
            content = response.content
            chunk_size = 50  # Characters per chunk
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield chunk
                
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Cohere is available."""
        return COHERE_AVAILABLE and self.api_key is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": "cohere",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "p": self.p,
            "k": self.k,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "available": self.is_available(),
            "supports_streaming": False,  # Cohere doesn't support true streaming yet
            "supports_async": True
        } 