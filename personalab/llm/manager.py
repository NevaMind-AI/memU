"""
LLM Manager for PersonaLab.

This module provides a unified interface to manage and switch between different LLM providers.
"""

import os
from typing import Any, Dict, List, Optional, Type

from .base import BaseLLM, LLMResponse
from .openai_llm import OpenAILLM
from .anthropic_llm import AnthropicLLM
from .local_llm import LocalLLM

# Import new providers with error handling
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


class LLMManager:
    """
    Manager class for handling multiple LLM providers.
    
    This class provides a convenient interface to work with different LLM providers,
    allowing easy switching between them and automatic fallback mechanisms.
    """
    
    def __init__(self, default_provider: Optional[str] = None):
        """
        Initialize LLM Manager.
        
        Args:
            default_provider: Default LLM provider to use ('openai', 'anthropic', 'local')
        """
        self.providers: Dict[str, BaseLLM] = {}
        self.default_provider = default_provider
        self.current_provider = None
        
        # Register available provider classes
        self.provider_classes = {
            'openai': OpenAILLM,
            'anthropic': AnthropicLLM,
            'local': LocalLLM
        }
        
        # Add new providers if available
        if GoogleLLM:
            self.provider_classes['google'] = GoogleLLM
        if AzureOpenAILLM:
            self.provider_classes['azure_openai'] = AzureOpenAILLM
        if CohereLLM:
            self.provider_classes['cohere'] = CohereLLM
        if BedrockLLM:
            self.provider_classes['bedrock'] = BedrockLLM
        if TogetherLLM:
            self.provider_classes['together'] = TogetherLLM
        if ReplicateLLM:
            self.provider_classes['replicate'] = ReplicateLLM
    
    def add_provider(
        self,
        name: str,
        provider_type: str,
        model_name: str,
        **kwargs
    ) -> None:
        """
        Add a new LLM provider.
        
        Args:
            name: Unique name for this provider instance
            provider_type: Type of provider ('openai', 'anthropic', 'google', 'azure_openai', 'cohere', 'bedrock', 'together', 'replicate', 'local')
            model_name: Name of the model to use
            **kwargs: Provider-specific configuration options
        """
        if provider_type not in self.provider_classes:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        provider_class = self.provider_classes[provider_type]
        provider_instance = provider_class(model_name, **kwargs)
        
        self.providers[name] = provider_instance
        
        # Set as current provider if it's the first one or matches default
        if self.current_provider is None or name == self.default_provider:
            self.current_provider = name
    
    def remove_provider(self, name: str) -> None:
        """Remove a provider."""
        if name in self.providers:
            del self.providers[name]
            if self.current_provider == name:
                self.current_provider = next(iter(self.providers), None)
    
    def set_current_provider(self, name: str) -> None:
        """Set the current active provider."""
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        self.current_provider = name
    
    def get_current_provider(self) -> Optional[BaseLLM]:
        """Get the current active provider instance."""
        if self.current_provider and self.current_provider in self.providers:
            return self.providers[self.current_provider]
        return None
    
    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using the specified or current provider.
        
        Args:
            prompt: The user prompt/message
            provider: Specific provider to use (if None, uses current provider)
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        llm = self._get_provider(provider)
        return llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def generate_with_memory(
        self,
        prompt: str,
        memory_context: Dict[str, Any],
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using memory context with the specified or current provider.
        
        Args:
            prompt: The user prompt/message
            memory_context: Memory search results to include as context
            provider: Specific provider to use (if None, uses current provider)
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        llm = self._get_provider(provider)
        return llm.generate_with_memory(
            prompt=prompt,
            memory_context=memory_context,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def generate_with_fallback(
        self,
        prompt: str,
        provider_order: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response with automatic fallback to other providers on failure.
        
        Args:
            prompt: The user prompt/message
            provider_order: List of providers to try in order (if None, tries all available)
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options
            
        Returns:
            LLMResponse object containing the generated content and metadata
            
        Raises:
            RuntimeError: If all providers fail
        """
        providers_to_try = provider_order or list(self.providers.keys())
        
        last_error = None
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue
            
            try:
                return self.generate(
                    prompt=prompt,
                    provider=provider_name,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            except Exception as e:
                last_error = e
                print(f"Provider '{provider_name}' failed: {e}")
                continue
        
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
    
    def _get_provider(self, provider: Optional[str] = None) -> BaseLLM:
        """Get provider instance by name or return current provider."""
        if provider:
            if provider not in self.providers:
                raise ValueError(f"Provider '{provider}' not found")
            return self.providers[provider]
        
        current = self.get_current_provider()
        if current is None:
            raise RuntimeError("No provider available")
        return current
    
    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """List all configured providers with their information."""
        result = {}
        for name, provider in self.providers.items():
            result[name] = {
                "model_info": provider.get_model_info(),
                "is_available": provider.is_available(),
                "is_current": name == self.current_provider
            }
        return result
    
    def check_provider_availability(self) -> Dict[str, bool]:
        """Check availability of all configured providers."""
        return {
            name: provider.is_available()
            for name, provider in self.providers.items()
        }
    
    def get_provider_models(self, provider: str) -> List[str]:
        """Get available models for a specific provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not found")
        
        llm = self.providers[provider]
        if hasattr(llm, 'list_available_models'):
            return llm.list_available_models()
        return []
    
    @classmethod
    def create_quick_setup(
        cls,
        openai_model: str = "gpt-3.5-turbo",
        anthropic_model: str = "claude-3-sonnet-20240229",
        google_model: str = "gemini-pro",
        azure_model: str = "gpt-4",
        cohere_model: str = "command",
        bedrock_model: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        together_model: str = "meta-llama/Llama-2-7b-chat-hf",
        replicate_model: str = "meta/llama-2-70b-chat",
        local_model: str = "llama2",
        local_backend: str = "ollama"
    ) -> 'LLMManager':
        """
        Create a LLM manager with all available providers pre-configured.
        
        Args:
            openai_model: OpenAI model to use
            anthropic_model: Anthropic model to use
            google_model: Google Gemini model to use
            azure_model: Azure OpenAI model to use
            cohere_model: Cohere model to use
            bedrock_model: AWS Bedrock model to use
            together_model: Together AI model to use
            replicate_model: Replicate model to use
            local_model: Local model to use
            local_backend: Backend for local model ('ollama' or 'huggingface')
            
        Returns:
            Configured LLMManager instance
        """
        manager = cls()
        
        # Try to add OpenAI provider
        try:
            if os.getenv("OPENAI_API_KEY"):
                manager.add_provider("openai", "openai", openai_model)
        except Exception as e:
            print(f"Could not add OpenAI provider: {e}")
        
        # Try to add Anthropic provider
        try:
            if os.getenv("ANTHROPIC_API_KEY"):
                manager.add_provider("anthropic", "anthropic", anthropic_model)
        except Exception as e:
            print(f"Could not add Anthropic provider: {e}")
        
        # Try to add Google provider
        try:
            if GoogleLLM and os.getenv("GOOGLE_API_KEY"):
                manager.add_provider("google", "google", google_model)
        except Exception as e:
            print(f"Could not add Google provider: {e}")
        
        # Try to add Azure OpenAI provider
        try:
            if AzureOpenAILLM and os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
                manager.add_provider("azure_openai", "azure_openai", azure_model)
        except Exception as e:
            print(f"Could not add Azure OpenAI provider: {e}")
        
        # Try to add Cohere provider
        try:
            if CohereLLM and os.getenv("COHERE_API_KEY"):
                manager.add_provider("cohere", "cohere", cohere_model)
        except Exception as e:
            print(f"Could not add Cohere provider: {e}")
        
        # Try to add AWS Bedrock provider
        try:
            if BedrockLLM and (os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE")):
                manager.add_provider("bedrock", "bedrock", bedrock_model)
        except Exception as e:
            print(f"Could not add Bedrock provider: {e}")
        
        # Try to add Together AI provider
        try:
            if TogetherLLM and os.getenv("TOGETHER_API_KEY"):
                manager.add_provider("together", "together", together_model)
        except Exception as e:
            print(f"Could not add Together AI provider: {e}")
        
        # Try to add Replicate provider
        try:
            if ReplicateLLM and os.getenv("REPLICATE_API_TOKEN"):
                manager.add_provider("replicate", "replicate", replicate_model)
        except Exception as e:
            print(f"Could not add Replicate provider: {e}")
        
        # Try to add local provider
        try:
            manager.add_provider("local", "local", local_model, backend=local_backend)
        except Exception as e:
            print(f"Could not add local provider: {e}")
        
        return manager
    
    def __str__(self) -> str:
        provider_list = list(self.providers.keys())
        current = self.current_provider or "None"
        return f"LLMManager(providers={provider_list}, current={current})"
    
    def __repr__(self) -> str:
        return f"<LLMManager: {len(self.providers)} providers, current={self.current_provider}>" 