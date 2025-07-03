"""
Anthropic (Claude) LLM Client Implementation
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseLLMClient, LLMResponse


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude Client Implementation"""

    def __init__(
        self, api_key: str = None, model: str = "claude-3-sonnet-20240229", **kwargs
    ):
        """
        Initialize Anthropic Client

        Args:
            api_key: Anthropic API key, retrieved from environment variable if None
            model: Default model
            **kwargs: Other configuration parameters
        """
        super().__init__(model=model, **kwargs)

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        # Lazy import Anthropic library
        self._client = None

    @property
    def client(self):
        """Lazy load Anthropic client"""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic library is required. Install with: pip install anthropic>=0.7.0"
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
        """Anthropic chat completion"""
        model = self.get_model(model)

        try:
            # Preprocess messages
            processed_messages = self._prepare_messages(messages)

            # Call Anthropic API
            response = self.client.messages.create(
                model=model,
                messages=processed_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Build response
            content = ""
            if response.content:
                # Claude returns content as a list
                content = "".join(
                    [block.text for block in response.content if hasattr(block, "text")]
                )

            usage = {
                "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                "completion_tokens": getattr(response.usage, "output_tokens", 0),
                "total_tokens": getattr(response.usage, "input_tokens", 0)
                + getattr(response.usage, "output_tokens", 0),
            }

            return LLMResponse(
                content=content, usage=usage, model=response.model, success=True
            )

        except Exception as e:
            logging.error(f"Anthropic API call failed: {e}")
            return self._handle_error(e, model)

    def _get_default_model(self) -> str:
        """Get Anthropic default model"""
        return "claude-3-sonnet-20240229"

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Preprocess Anthropic message format"""
        processed = []

        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                role = msg["role"]
                content = str(msg["content"])

                # Anthropic role mapping
                if role == "system":
                    # Claude doesn't support system role, need to convert to user message
                    processed.append({"role": "user", "content": f"System: {content}"})
                elif role in ["user", "assistant"]:
                    processed.append({"role": role, "content": content})
                else:
                    logging.warning(f"Unknown role '{role}', treating as user")
                    processed.append({"role": "user", "content": content})
            else:
                logging.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "AnthropicClient":
        """Create Anthropic client from environment variables"""
        return cls()

    def __str__(self) -> str:
        return f"AnthropicClient(model={self.default_model})"
