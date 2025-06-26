"""
Azure OpenAI LLM implementation for PersonaLab.

This module provides support for Azure OpenAI models through the Azure OpenAI API.
"""

import os
import time
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    from openai import AzureOpenAI, AsyncAzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False
    AzureOpenAI = None
    AsyncAzureOpenAI = None

from .base import BaseLLM, LLMResponse


class AzureOpenAILLM(BaseLLM):
    """
    Azure OpenAI LLM implementation.
    
    Supports Azure-deployed OpenAI models like:
    - gpt-4
    - gpt-4-turbo
    - gpt-3.5-turbo
    - gpt-4o
    """
    
    def __init__(self, 
                 model: str = "gpt-4",
                 azure_endpoint: Optional[str] = None,
                 api_key: Optional[str] = None,
                 api_version: str = "2024-02-15-preview",
                 deployment_name: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 top_p: float = 1.0,
                 frequency_penalty: float = 0.0,
                 presence_penalty: float = 0.0,
                 **kwargs):
        """
        Initialize Azure OpenAI LLM.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            azure_endpoint: Azure endpoint URL
            api_key: Azure OpenAI API key
            api_version: API version to use
            deployment_name: Deployment name (if different from model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            **kwargs: Additional model parameters
        """
        if not AZURE_OPENAI_AVAILABLE:
            raise ImportError(
                "Azure OpenAI library not available. Install with: "
                "pip install openai"
            )
        
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        
        # Set up Azure configuration
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY") 
        self.api_version = api_version
        self.deployment_name = deployment_name or model
        
        if not self.azure_endpoint:
            raise ValueError(
                "Azure endpoint not provided. Set AZURE_OPENAI_ENDPOINT environment variable "
                "or pass azure_endpoint parameter"
            )
        
        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key not provided. Set AZURE_OPENAI_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.kwargs = kwargs
        
        # Initialize clients
        self._client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
        
        self._async_client = AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
    
    async def generate_async(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           memory_context: Optional[str] = None,
                           **kwargs) -> LLMResponse:
        """
        Generate response asynchronously using Azure OpenAI.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add memory context
            if memory_context:
                messages.append({"role": "system", "content": f"Context: {memory_context}"})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Prepare parameters
            params = {
                "model": self.deployment_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty)
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make API call
            response = await self._async_client.chat.completions.create(**params)
            
            # Extract response
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="azure_openai",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                response_time=end_time - start_time,
                finish_reason=finish_reason
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="azure_openai",
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
        Generate response synchronously using Azure OpenAI.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add memory context
            if memory_context:
                messages.append({"role": "system", "content": f"Context: {memory_context}"})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Prepare parameters
            params = {
                "model": self.deployment_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty)
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make API call
            response = self._client.chat.completions.create(**params)
            
            # Extract response
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="azure_openai",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                response_time=end_time - start_time,
                finish_reason=finish_reason
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="azure_openai",
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
        Stream response asynchronously using Azure OpenAI.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Yields:
            Streaming text chunks
        """
        try:
            # Prepare messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add memory context
            if memory_context:
                messages.append({"role": "system", "content": f"Context: {memory_context}"})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Prepare parameters
            params = {
                "model": self.deployment_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
                "stream": True
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Make streaming API call
            stream = await self._async_client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Azure OpenAI is available."""
        return (AZURE_OPENAI_AVAILABLE and 
                self.azure_endpoint is not None and 
                self.api_key is not None)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": "azure_openai",
            "model": self.model,
            "deployment_name": self.deployment_name,
            "azure_endpoint": self.azure_endpoint,
            "api_version": self.api_version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "available": self.is_available(),
            "supports_streaming": True,
            "supports_async": True
        } 