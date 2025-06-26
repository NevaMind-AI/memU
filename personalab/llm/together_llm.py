"""
Together AI LLM implementation for PersonaLab.

This module provides support for Together AI models through their API.
"""

import os
import time
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    import together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    together = None

from .base import BaseLLM, LLMResponse


class TogetherLLM(BaseLLM):
    """
    Together AI LLM implementation.
    
    Supports Together AI models like:
    - meta-llama/Llama-2-7b-chat-hf
    - meta-llama/Llama-2-13b-chat-hf
    - meta-llama/Llama-2-70b-chat-hf
    - mistralai/Mixtral-8x7B-Instruct-v0.1
    - NousResearch/Nous-Hermes-2-Yi-34B
    """
    
    def __init__(self, 
                 model: str = "meta-llama/Llama-2-7b-chat-hf",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 top_p: float = 1.0,
                 top_k: int = 50,
                 repetition_penalty: float = 1.0,
                 **kwargs):
        """
        Initialize Together AI LLM.
        
        Args:
            model: Model name (e.g., 'meta-llama/Llama-2-7b-chat-hf')
            api_key: Together AI API key (if not provided, uses TOGETHER_API_KEY env var)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            repetition_penalty: Repetition penalty
            **kwargs: Additional model parameters
        """
        if not TOGETHER_AVAILABLE:
            raise ImportError(
                "Together AI library not available. Install with: "
                "pip install together"
            )
        
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        
        # Set up API key
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Together AI API key not provided. Set TOGETHER_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens or 512
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty
        self.kwargs = kwargs
        
        # Set API key
        together.api_key = self.api_key
    
    async def generate_async(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           memory_context: Optional[str] = None,
                           **kwargs) -> LLMResponse:
        """
        Generate response asynchronously using Together AI.
        
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
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "repetition_penalty": kwargs.get("repetition_penalty", self.repetition_penalty)
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make API call (Together doesn't have async client, so we'll simulate)
            response = together.Complete.create(**params)
            
            # Extract response
            content = response["output"]["choices"][0]["text"]
            finish_reason = response["output"]["choices"][0].get("finish_reason", "stop")
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="together",
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
                provider="together",
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
        Generate response synchronously using Together AI.
        
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
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "repetition_penalty": kwargs.get("repetition_penalty", self.repetition_penalty)
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make API call
            response = together.Complete.create(**params)
            
            # Extract response
            content = response["output"]["choices"][0]["text"]
            finish_reason = response["output"]["choices"][0].get("finish_reason", "stop")
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="together",
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
                provider="together",
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
        Stream response asynchronously using Together AI.
        
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
            
            # Prepare parameters
            params = {
                "model": self.model,
                "prompt": full_prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "repetition_penalty": kwargs.get("repetition_penalty", self.repetition_penalty),
                "stream_tokens": True
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make streaming API call
            for chunk in together.Complete.create_streaming(**params):
                if chunk.get("choices") and len(chunk["choices"]) > 0:
                    token = chunk["choices"][0].get("text", "")
                    if token:
                        yield token
                        
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Together AI is available."""
        return TOGETHER_AVAILABLE and self.api_key is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": "together",
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