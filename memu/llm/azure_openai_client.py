"""
Azure OpenAI LLM Client Implementation
"""

import logging
import os
from typing import Dict, List

from .base import BaseLLMClient, LLMResponse


class AzureOpenAIClient(BaseLLMClient):
    """Azure OpenAI Client Implementation"""

    def __init__(
        self,
        api_key: str = None,
        azure_endpoint: str = None,
        api_version: str = "2025-01-01-preview",
        deployment_name: str = "gpt-4o-mini",
        use_entra_id: bool = False,
        **kwargs,
    ):
        """
        Initialize Azure OpenAI Client

        Args:
            api_key: Azure OpenAI API key (not needed if using Entra ID)
            azure_endpoint: Azure OpenAI endpoint URL
            api_version: Azure OpenAI API version
            deployment_name: Azure OpenAI deployment name
            use_entra_id: Whether to use Entra ID authentication
            **kwargs: Other configuration parameters
        """
        super().__init__(model=deployment_name, **kwargs)

        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv(
            "AZURE_OPENAI_ENDPOINT", "https://openaialluci.openai.azure.com/"
        )
        self.api_version = api_version
        self.deployment_name = deployment_name or os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"
        )
        self.use_entra_id = use_entra_id

        if not self.use_entra_id and not self.api_key:
            raise ValueError(
                "Azure OpenAI API key is required when not using Entra ID. "
                "Set AZURE_OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        if not self.azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. "
                "Set AZURE_OPENAI_ENDPOINT environment variable or pass azure_endpoint parameter."
            )

        # Lazy import Azure OpenAI library
        self._client = None

    @property
    def client(self):
        """Lazy load Azure OpenAI client"""
        if self._client is None:
            try:
                from openai import AzureOpenAI

                if self.use_entra_id:
                    # Use Entra ID authentication
                    from azure.identity import (
                        DefaultAzureCredential,
                        get_bearer_token_provider,
                    )

                    token_provider = get_bearer_token_provider(
                        DefaultAzureCredential(),
                        "https://cognitiveservices.azure.com/.default",
                    )

                    self._client = AzureOpenAI(
                        azure_endpoint=self.azure_endpoint,
                        azure_ad_token_provider=token_provider,
                        api_version=self.api_version,
                    )
                else:
                    # Use API key authentication
                    self._client = AzureOpenAI(
                        api_key=self.api_key,
                        azure_endpoint=self.azure_endpoint,
                        api_version=self.api_version,
                    )

            except ImportError as e:
                if "azure.identity" in str(e):
                    raise ImportError(
                        "Azure Identity library is required for Entra ID authentication. "
                        "Install with: pip install azure-identity"
                    )
                else:
                    raise ImportError(
                        "OpenAI library is required. Install with: pip install openai>=1.0.0"
                    )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 8000,
        tools: List[Dict] = None,
        tool_choice: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Azure OpenAI chat completion with function calling support"""
        # For Azure OpenAI, we use the deployment name instead of model name
        deployment = model or self.deployment_name

        try:
            # Preprocess messages
            processed_messages = self._prepare_messages(messages)

            # Prepare API call parameters
            api_params = {
                "model": deployment,
                "messages": processed_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add function calling parameters if provided
            if tools:
                api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice

            # Call Azure OpenAI API
            response = self.client.chat.completions.create(**api_params)

            # Extract tool calls if present
            tool_calls = None
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = message.tool_calls

            # Build response
            return LLMResponse(
                content=message.content or "",
                usage=response.usage.model_dump() if response.usage else {},
                model=response.model,
                success=True,
                tool_calls=tool_calls,
            )

        except Exception as e:
            logging.error(f"Azure OpenAI API call failed: {e}")
            return self._handle_error(e, deployment)

    def _get_default_model(self) -> str:
        """Get Azure OpenAI default deployment"""
        return self.deployment_name

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Preprocess Azure OpenAI message format"""
        # Ensure message format is correct
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg:
                # Base message with role
                processed_msg = {"role": msg["role"]}

                # Add content if present
                if "content" in msg:
                    processed_msg["content"] = (
                        str(msg["content"]) if msg["content"] is not None else None
                    )

                # Preserve function calling fields
                if "tool_calls" in msg:
                    processed_msg["tool_calls"] = msg["tool_calls"]

                if "tool_call_id" in msg:
                    processed_msg["tool_call_id"] = msg["tool_call_id"]

                processed.append(processed_msg)
            else:
                logging.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "AzureOpenAIClient":
        """Create Azure OpenAI client from environment variables"""
        return cls()

    def __str__(self) -> str:
        return f"AzureOpenAIClient(deployment={self.deployment_name}, endpoint={self.azure_endpoint})"
