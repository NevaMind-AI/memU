"""
OpenAI LLM Client Implementation
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseLLMClient, LLMResponse


class OpenAIClient(BaseLLMClient):
    """OpenAI Client Implementation"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = "gpt-3.5-turbo",
        **kwargs,
    ):
        """
        Initialize OpenAI Client

        Args:
            api_key: OpenAI API key, retrieved from environment variable if None
            base_url: API base URL, supports custom endpoints
            model: Default model
            **kwargs: Other configuration parameters
        """
        super().__init__(model=model, **kwargs)

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        # Lazy import OpenAI library
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            try:
                import openai

                # Create OpenAI client with only api_key and base_url
                # Explicitly avoid passing any other parameters that might cause issues
                client_params = {}
                if self.api_key:
                    client_params['api_key'] = self.api_key
                if self.base_url:
                    client_params['base_url'] = self.base_url
                
                self._client = openai.OpenAI(**client_params)
            except ImportError:
                raise ImportError(
                    "OpenAI library is required. Install with: pip install openai>=1.0.0"
                )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        """OpenAI chat completion"""
        model = self.get_model(model)

        try:
            # Debug: Log all incoming parameters
            print(f"DEBUG OpenAI: chat_completion kwargs: {kwargs}")
            print(f"DEBUG OpenAI: self.config: {self.config}")
            
            # Preprocess messages
            processed_messages = self._prepare_messages(messages)

            # Filter out parameters that should not be passed to OpenAI API
            api_params = self._filter_api_params(kwargs)
            print(f"DEBUG OpenAI: filtered api_params: {api_params}")

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=processed_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **api_params,
            )

            # Build response
            return LLMResponse(
                content=response.choices[0].message.content,
                usage=response.usage.model_dump() if response.usage else {},
                model=response.model,
                success=True,
            )

        except Exception as e:
            logging.error(f"OpenAI API call failed: {e}")
            return self._handle_error(e, model)

    def _filter_api_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out parameters that should not be passed to OpenAI API"""
        # Only exclude API client configuration parameters
        excluded_params = {"api_key", "base_url"}

        return {k: v for k, v in params.items() if k not in excluded_params}

    def _get_default_model(self) -> str:
        """Get OpenAI default model"""
        return "gpt-3.5-turbo"

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Preprocess OpenAI message format"""
        # Ensure message format is correct
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                processed.append({"role": msg["role"], "content": str(msg["content"])})
            else:
                logging.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "OpenAIClient":
        """Create OpenAI client from environment variables"""
        return cls()

    def __str__(self) -> str:
        return f"OpenAIClient(model={self.default_model}, base_url={self.base_url})"
