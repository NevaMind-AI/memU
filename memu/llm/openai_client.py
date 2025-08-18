"""
OpenAI LLM Client Implementation
"""

import os
from typing import Dict, List

from .base import BaseLLMClient, LLMResponse
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI Client Implementation"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = "gpt-4.1-mini",
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
        # Only use custom base_url if explicitly provided as a parameter
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")

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
                    client_params["api_key"] = self.api_key
                # Only set base_url if provided
                if self.base_url:
                    client_params["base_url"] = self.base_url

                # Debug prints removed for production use

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
        max_tokens: int = None,
        **kwargs,
    ) -> LLMResponse:
        """OpenAI chat completion"""
        model = self.get_model(model)
        resolved_max_tokens = self._get_max_tokens(max_tokens)

        try:

            # Preprocess messages
            processed_messages = self._prepare_messages(messages)

            # Call OpenAI API
            api_kwargs = {
                "model": model,
                "messages": processed_messages,
                "temperature": temperature,
                "max_tokens": resolved_max_tokens,
            }

            # Add function calling parameters if provided
            if "tools" in kwargs:
                api_kwargs["tools"] = kwargs["tools"]
            if "tool_choice" in kwargs:
                api_kwargs["tool_choice"] = kwargs["tool_choice"]

            response = self.client.chat.completions.create(**api_kwargs)

            # Build response
            response_data = {
                "content": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else {},
                "model": response.model,
                "success": True,
            }

            # Include tool calls if present
            if (
                hasattr(response.choices[0].message, "tool_calls")
                and response.choices[0].message.tool_calls
            ):
                response_data["tool_calls"] = response.choices[0].message.tool_calls

            return LLMResponse(**response_data)

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return self._handle_error(e, model)

    def _get_default_model(self) -> str:
        """Get OpenAI default model"""
        return "gpt-4o-mini"

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Preprocess OpenAI message format"""
        # Ensure message format is correct
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg:
                processed_msg = {"role": msg["role"]}

                # Handle content (may be None for tool calls)
                if "content" in msg and msg["content"] is not None:
                    processed_msg["content"] = str(msg["content"])
                elif msg["role"] != "assistant" or "tool_calls" not in msg:
                    # Only require content if not an assistant message with tool calls
                    processed_msg["content"] = ""

                # Handle tool calls (for assistant messages)
                if "tool_calls" in msg:
                    processed_msg["tool_calls"] = msg["tool_calls"]

                # Handle tool call ID (for tool messages)
                if "tool_call_id" in msg:
                    processed_msg["tool_call_id"] = msg["tool_call_id"]
                    processed_msg["content"] = str(msg.get("content", ""))

                processed.append(processed_msg)
            else:
                logger.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "OpenAIClient":
        """Create OpenAI client from environment variables"""
        return cls()

    def __str__(self) -> str:
        return f"OpenAIClient(model={self.default_model}, base_url={self.base_url})"
