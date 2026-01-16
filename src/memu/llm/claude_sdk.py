"""Claude SDK client for Anthropic's Claude API.

This module provides an async client for Claude that mirrors the OpenAI SDK client interface,
enabling seamless integration with MemU's LLM abstraction layer.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class ClaudeUsage:
    """Token usage information from Claude API."""

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ClaudeMessage:
    """Claude message response."""

    id: str
    type: str
    role: str
    content: list[dict[str, Any]]
    model: str
    stop_reason: str | None
    stop_sequence: str | None
    usage: ClaudeUsage

    @property
    def text(self) -> str:
        """Extract text content from response."""
        text_parts = []
        for block in self.content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "".join(text_parts)


class ClaudeSDKClient:
    """Anthropic Claude LLM client using the official Python SDK.

    Provides async methods for chat completions and vision that match
    the interface expected by MemU's LLM wrapper.
    """

    def __init__(
        self,
        *,
        api_key: str,
        chat_model: str = "claude-opus-4-5-20251124",
        base_url: str | None = None,
        embed_model: str | None = None,
    ):
        """Initialize Claude SDK client.

        Args:
            api_key: Anthropic API key
            chat_model: Model to use for chat (default: claude-opus-4-5-20251124)
            base_url: Optional custom base URL for API
            embed_model: Not used (Claude doesn't have embedding API), kept for interface compatibility
        """
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            msg = "anthropic package is required for Claude support. Install with: pip install anthropic"
            raise ImportError(msg) from exc

        self.api_key = api_key
        self.chat_model = chat_model
        self.embed_model = embed_model  # Claude doesn't support embeddings natively

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = AsyncAnthropic(**client_kwargs)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, ClaudeMessage]:
        """Generate a summary using Claude.

        Args:
            text: Text to summarize
            max_tokens: Maximum tokens in response (default: 4096)
            system_prompt: Optional system prompt

        Returns:
            Tuple of (summary text, raw ClaudeMessage response)
        """
        prompt = system_prompt or "Summarize the text in one short paragraph."

        response = await self.client.messages.create(
            model=self.chat_model,
            max_tokens=max_tokens or 4096,
            system=prompt,
            messages=[{"role": "user", "content": text}],
        )

        # Convert to our dataclass for consistent interface
        message = self._parse_response(response)
        logger.debug("Claude summarize response: %s", message)
        return message.text, message

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, ClaudeMessage]:
        """Call Claude Vision API with an image.

        Args:
            prompt: Text prompt to send with the image
            image_path: Path to the image file
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            Tuple of (LLM response text, raw ClaudeMessage response)
        """
        # Read and encode image as base64
        image_data = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Detect image format
        suffix = Path(image_path).suffix.lower()
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(suffix, "image/jpeg")

        # Build content with image and text
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_image,
                },
            },
            {"type": "text", "text": prompt},
        ]

        kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "max_tokens": max_tokens or 4096,
            "messages": [{"role": "user", "content": content}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)

        message = self._parse_response(response)
        logger.debug("Claude vision response: %s", message)
        return message.text, message

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        """Create text embeddings.

        Note: Claude does not have a native embedding API.
        This method raises NotImplementedError.

        For embeddings with Claude, use a separate embedding provider like:
        - OpenAI's text-embedding-3-small
        - Voyage AI (Anthropic's recommended embedding partner)
        - Cohere embeddings

        Args:
            inputs: List of texts to embed

        Raises:
            NotImplementedError: Claude doesn't support embeddings
        """
        msg = (
            "Claude does not have a native embedding API. "
            "Use a separate embedding provider (OpenAI, Voyage AI, or Cohere) for embeddings."
        )
        raise NotImplementedError(msg)

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: Literal["text", "json", "verbose_json"] = "text",
    ) -> tuple[str, Any]:
        """Transcribe audio file.

        Note: Claude does not have a native audio transcription API.
        This method raises NotImplementedError.

        For audio transcription, use a separate provider like:
        - OpenAI's Whisper API
        - AssemblyAI
        - Deepgram

        Args:
            audio_path: Path to the audio file
            prompt: Optional prompt to guide transcription
            language: Optional language code
            response_format: Response format

        Raises:
            NotImplementedError: Claude doesn't support audio transcription
        """
        msg = (
            "Claude does not have a native audio transcription API. "
            "Use a separate provider (OpenAI Whisper, AssemblyAI, or Deepgram) for transcription."
        )
        raise NotImplementedError(msg)

    def _parse_response(self, response: Any) -> ClaudeMessage:
        """Parse Anthropic SDK response into our dataclass."""
        usage = ClaudeUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        # Convert content blocks to dicts
        content = []
        for block in response.content:
            if hasattr(block, "text"):
                content.append({"type": "text", "text": block.text})
            elif hasattr(block, "type"):
                content.append({"type": block.type})

        return ClaudeMessage(
            id=response.id,
            type=response.type,
            role=response.role,
            content=content,
            model=response.model,
            stop_reason=response.stop_reason,
            stop_sequence=response.stop_sequence,
            usage=usage,
        )


__all__ = ["ClaudeMessage", "ClaudeSDKClient", "ClaudeUsage"]
