"""
Replicate LLM implementation for PersonaLab.

This module provides support for Replicate models through their API.
"""

import os
import time
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    replicate = None

from .base import BaseLLM, LLMResponse


class ReplicateLLM(BaseLLM):
    """
    Replicate LLM implementation.
    
    Supports Replicate models like:
    - meta/llama-2-70b-chat
    - mistralai/mixtral-8x7b-instruct-v0.1
    - stability-ai/sdxl
    - And many other open-source models
    """
    
    def __init__(self, 
                 model: str = "meta/llama-2-70b-chat",
                 api_token: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 top_p: float = 1.0,
                 top_k: int = 50,
                 repetition_penalty: float = 1.0,
                 **kwargs):
        """
        Initialize Replicate LLM.
        
        Args:
            model: Model name (e.g., 'meta/llama-2-70b-chat')
            api_token: Replicate API token (if not provided, uses REPLICATE_API_TOKEN env var)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            repetition_penalty: Repetition penalty
            **kwargs: Additional model parameters
        """
        if not REPLICATE_AVAILABLE:
            raise ImportError(
                "Replicate library not available. Install with: "
                "pip install replicate"
            )
        
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        
        # Set up API token
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "Replicate API token not provided. Set REPLICATE_API_TOKEN environment variable "
                "or pass api_token parameter"
            )
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens or 512
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty
        self.kwargs = kwargs
        
        # Set API token
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
    
    async def generate_async(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           memory_context: Optional[str] = None,
                           **kwargs) -> LLMResponse:
        """
        Generate response asynchronously using Replicate.
        
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
            
            # Prepare input parameters for Replicate
            input_params = {
                "prompt": full_prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "repetition_penalty": kwargs.get("repetition_penalty", self.repetition_penalty)
            }
            
            # Remove None values
            input_params = {k: v for k, v in input_params.items() if v is not None}
            
            # Make API call (async)
            output = await replicate.async_run(self.model, input=input_params)
            
            # Combine output (Replicate returns a list of strings)
            if isinstance(output, list):
                content = "".join(output)
            else:
                content = str(output)
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="replicate",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason="stop"
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="replicate",
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
        Generate response synchronously using Replicate.
        
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
            
            # Prepare input parameters for Replicate
            input_params = {
                "prompt": full_prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "repetition_penalty": kwargs.get("repetition_penalty", self.repetition_penalty)
            }
            
            # Remove None values
            input_params = {k: v for k, v in input_params.items() if v is not None}
            
            # Make API call
            output = replicate.run(self.model, input=input_params)
            
            # Combine output (Replicate returns a list of strings)
            if isinstance(output, list):
                content = "".join(output)
            else:
                content = str(output)
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="replicate",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason="stop"
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="replicate",
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
        Stream response asynchronously using Replicate.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Yields:
            Streaming text chunks
        """
        try:
            # Construct full prompt
            full_prompt = self._construct_prompt(prompt, system_prompt, memory_context)
            
            # Prepare input parameters for Replicate
            input_params = {
                "prompt": full_prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "repetition_penalty": kwargs.get("repetition_penalty", self.repetition_penalty)
            }
            
            # Remove None values
            input_params = {k: v for k, v in input_params.items() if v is not None}
            
            # Make streaming API call
            async for event in replicate.async_stream(self.model, input=input_params):
                yield str(event)
                        
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Replicate is available."""
        return REPLICATE_AVAILABLE and self.api_token is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": "replicate",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "available": self.is_available(),
            "supports_streaming": True,
            "supports_async": True
        } 