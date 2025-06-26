"""
Google Gemini LLM implementation for PersonaLab.

This module provides support for Google's Gemini models through the Google AI API.
"""

import os
import time
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    genai = None

from .base import BaseLLM, LLMResponse


class GoogleLLM(BaseLLM):
    """
    Google Gemini LLM implementation.
    
    Supports models like:
    - gemini-pro
    - gemini-pro-vision
    - gemini-1.5-pro
    - gemini-1.5-flash
    """
    
    def __init__(self, 
                 model: str = "gemini-pro",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 top_p: float = 1.0,
                 top_k: Optional[int] = None,
                 **kwargs):
        """
        Initialize Google Gemini LLM.
        
        Args:
            model: Model name (e.g., 'gemini-pro', 'gemini-1.5-pro')
            api_key: Google AI API key (if not provided, uses GOOGLE_API_KEY env var)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            **kwargs: Additional model parameters
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google AI library not available. Install with: "
                "pip install google-generativeai"
            )
        
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        
        # Set up API key
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key not provided. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.kwargs = kwargs
        
        # Initialize the model
        self._model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the Gemini model."""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=self.temperature,
                top_p=self.top_p,
                max_output_tokens=self.max_tokens,
                **({"top_k": self.top_k} if self.top_k else {})
            )
            
            self._model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Gemini model: {e}")
    
    async def generate_async(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           memory_context: Optional[str] = None,
                           **kwargs) -> LLMResponse:
        """
        Generate response asynchronously using Google Gemini.
        
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
            
            # Override generation config if kwargs provided
            generation_config = None
            if kwargs:
                config_params = {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", self.top_p),
                    "max_output_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
                if "top_k" in kwargs or self.top_k:
                    config_params["top_k"] = kwargs.get("top_k", self.top_k)
                
                generation_config = genai.types.GenerationConfig(**config_params)
            
            # Generate response
            if generation_config:
                response = await self._model.generate_content_async(
                    full_prompt,
                    generation_config=generation_config
                )
            else:
                response = await self._model.generate_content_async(full_prompt)
            
            # Extract response text
            response_text = response.text if response.text else ""
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(response_text)
            
            end_time = time.time()
            
            return LLMResponse(
                content=response_text,
                model=self.model,
                provider="google",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason="stop" if response.text else "error"
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="google",
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
        Generate response synchronously using Google Gemini.
        
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
            
            # Override generation config if kwargs provided
            generation_config = None
            if kwargs:
                config_params = {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", self.top_p),
                    "max_output_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
                if "top_k" in kwargs or self.top_k:
                    config_params["top_k"] = kwargs.get("top_k", self.top_k)
                
                generation_config = genai.types.GenerationConfig(**config_params)
            
            # Generate response
            if generation_config:
                response = self._model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            else:
                response = self._model.generate_content(full_prompt)
            
            # Extract response text
            response_text = response.text if response.text else ""
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(response_text)
            
            end_time = time.time()
            
            return LLMResponse(
                content=response_text,
                model=self.model,
                provider="google",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason="stop" if response.text else "error"
            )
            
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="google",
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
        Stream response asynchronously using Google Gemini.
        
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
            
            # Override generation config if kwargs provided
            generation_config = None
            if kwargs:
                config_params = {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", self.top_p),
                    "max_output_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
                if "top_k" in kwargs or self.top_k:
                    config_params["top_k"] = kwargs.get("top_k", self.top_k)
                
                generation_config = genai.types.GenerationConfig(**config_params)
            
            # Generate streaming response
            if generation_config:
                response = await self._model.generate_content_async(
                    full_prompt,
                    generation_config=generation_config,
                    stream=True
                )
            else:
                response = await self._model.generate_content_async(
                    full_prompt,
                    stream=True
                )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Google Gemini is available."""
        return GOOGLE_AVAILABLE and self.api_key is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": "google",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "available": self.is_available(),
            "supports_streaming": True,
            "supports_async": True
        } 