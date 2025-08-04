"""
DeepSeek LLM Client Implementation using Azure AI Inference
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseLLMClient, LLMResponse

# Try to import Azure AI Inference components
try:
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import (
        AssistantMessage,
        SystemMessage,
        ToolMessage,
        UserMessage,
    )
    from azure.core.credentials import AzureKeyCredential

    AZURE_AI_INFERENCE_AVAILABLE = True
except ImportError as e:
    AZURE_AI_INFERENCE_AVAILABLE = False
    _import_error = str(e)


class DeepSeekClient(BaseLLMClient):
    """DeepSeek Client Implementation using Azure AI Inference"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model_name: str = "DeepSeek-V3-0324",
        api_version: str = "2024-05-01-preview",
        **kwargs,
    ):
        """
        Initialize DeepSeek Client

        Args:
            api_key: DeepSeek API key
            endpoint: DeepSeek endpoint URL
            model_name: DeepSeek model name
            api_version: API version
            **kwargs: Other configuration parameters
        """
        super().__init__(model=model_name, **kwargs)

        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.endpoint = endpoint or os.getenv("DEEPSEEK_ENDPOINT")
        self.model_name = model_name
        self.api_version = api_version

        if not self.api_key:
            raise ValueError(
                "DeepSeek API key is required. "
                "Set DEEPSEEK_API_KEY environment variable or pass api_key parameter."
            )

        if not self.endpoint:
            raise ValueError(
                "DeepSeek endpoint is required. "
                "Set DEEPSEEK_ENDPOINT environment variable or pass endpoint parameter."
            )

        # Check if Azure AI Inference is available
        if not AZURE_AI_INFERENCE_AVAILABLE:
            raise ImportError(
                f"Azure AI Inference library is required but not available: {_import_error}. "
                "Install with: pip install azure-ai-inference"
            )

        # Lazy import Azure AI Inference library
        self._client = None

    @property
    def client(self):
        """Lazy load DeepSeek client"""
        if self._client is None:
            # Type assertion safe because we validate in __init__
            assert self.api_key is not None, "API key should not be None at this point"
            assert (
                self.endpoint is not None
            ), "Endpoint should not be None at this point"

            self._client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
                api_version=self.api_version,
            )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """DeepSeek chat completion with function calling support"""
        model_name = model or self.model_name

        try:
            # Preprocess messages to Azure AI Inference format
            processed_messages = self._prepare_messages(messages)

            # Prepare API call parameters
            api_params = {
                "messages": processed_messages,
                "model": model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": kwargs.get("top_p", 1.0),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            }

            # Add function calling parameters if provided
            if tools:
                api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice

            # Call DeepSeek API via Azure AI Inference
            response = self.client.complete(**api_params)

            # Extract tool calls if present
            tool_calls = None
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = message.tool_calls

            # Extract usage information
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(
                        response.usage, "completion_tokens", 0
                    ),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                }

            # Build response
            return LLMResponse(
                content=message.content or "",
                usage=usage,
                model=model_name,
                success=True,
                tool_calls=tool_calls,
            )

        except Exception as e:
            logging.error(f"DeepSeek API call failed: {e}")
            return self._handle_error(e, model_name)

    def _get_default_model(self) -> str:
        """Get DeepSeek default model"""
        return self.model_name

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Any]:
        """Preprocess messages to Azure AI Inference format"""
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg:
                role = msg["role"]
                content = msg.get("content", "")

                if role == "system":
                    processed.append(SystemMessage(content=content))
                elif role == "user":
                    processed.append(UserMessage(content=content))
                elif role == "assistant":
                    if "tool_calls" in msg:
                        # Handle assistant message with tool calls
                        processed.append(
                            AssistantMessage(
                                content=content, tool_calls=msg["tool_calls"]
                            )
                        )
                    else:
                        processed.append(AssistantMessage(content=content))
                elif role == "tool":
                    # Handle tool response messages
                    processed.append(
                        ToolMessage(
                            content=content, tool_call_id=msg.get("tool_call_id", "")
                        )
                    )
                else:
                    logging.warning(
                        f"Unknown message role: {role}, treating as user message"
                    )
                    processed.append(UserMessage(content=content))
            else:
                logging.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "DeepSeekClient":
        """Create DeepSeek client from environment variables"""
        return cls()

    def __str__(self) -> str:
        return f"DeepSeekClient(model={self.model_name}, endpoint={self.endpoint})"
