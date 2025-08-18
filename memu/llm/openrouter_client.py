"""
OpenRouter LLM Client Implementation using OpenRouter's OpenAI-compatible API
"""

import os
from typing import Any, Dict, List, Optional

from .base import BaseLLMClient, LLMResponse
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OpenRouterClient(BaseLLMClient):
    """OpenRouter Client Implementation using OpenAI API library."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize OpenRouter Client

        Args:
            api_key: OpenRouter API key
            endpoint: OpenRouter endpoint URL
            model_name: OpenRouter model name
            **kwargs: Other configuration parameters
        """
        # Resolve from environment first, then fall back to provided args
        resolved_model = (
            os.getenv("MEMU_OPENROUTER_MODEL") or model_name or "openrouter/auto"
        )
        super().__init__(model=resolved_model, **kwargs)

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        # OpenRouter OpenAI-compatible base URL
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
        self.model_name = resolved_model

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is required. "
                "Set OPENROUTER_API_KEY environment variable or pass api_key parameter."
            )
        self._client = None

    @property
    def client(self):
        """Lazy load OpenRouter client (OpenAI-compatible)"""
        if self._client is None:
            try:
                import openai

                self._client = openai.OpenAI(
                    api_key=self.api_key, base_url=self.base_url
                )
            except ImportError:
                raise ImportError(
                    "OpenAI library is required. Install with: pip install openai>=1.0.0"
                )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """OpenRouter chat completion with function calling support"""
        model_name = model or self.model_name
        resolved_max_tokens = self._get_max_tokens(max_tokens)

        try:
            # Preprocess messages (OpenAI format)
            processed_messages = self._prepare_messages(messages)

            # Prepare API call parameters
            api_params = {
                "model": model_name,
                "messages": processed_messages,
                "temperature": temperature,
                "max_tokens": resolved_max_tokens,
            }

            # Add function calling parameters if provided
            if tools:
                api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice

            # Call OpenRouter API (OpenAI-compatible)
            response = self.client.chat.completions.create(**api_params)

            # Extract tool calls if present
            tool_calls = None
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = message.tool_calls

            # Extract usage information
            usage = (
                response.usage.model_dump() if getattr(response, "usage", None) else {}
            )

            # Build response
            return LLMResponse(
                content=message.content or "",
                usage=usage,
                model=model_name,
                success=True,
                tool_calls=tool_calls,
            )

        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            return self._handle_error(e, model_name)

    def _get_default_model(self) -> str:
        """Get OpenRouter default model"""
        return self.model_name

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Preprocess messages in OpenAI-compatible format"""
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg:
                processed_msg = {"role": msg["role"]}
                if "content" in msg and msg["content"] is not None:
                    processed_msg["content"] = str(msg["content"])
                elif msg["role"] != "assistant" or "tool_calls" not in msg:
                    processed_msg["content"] = ""
                if "tool_calls" in msg:
                    processed_msg["tool_calls"] = msg["tool_calls"]
                if "tool_call_id" in msg:
                    processed_msg["tool_call_id"] = msg["tool_call_id"]
                    processed_msg["content"] = str(msg.get("content", ""))
                processed.append(processed_msg)
            else:
                logger.warning(f"Invalid message format: {msg}")
        return processed

    @classmethod
    def from_env(cls) -> "OpenRouterClient":
        """Create OpenRouter client from environment variables"""
        return cls()

    def __str__(self) -> str:
        return f"OpenRouterClient(model={self.model_name}, endpoint={self.endpoint})"
