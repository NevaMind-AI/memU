from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from pathlib import Path

import httpx

from memu.llm.backends.base import LLMBackend
from memu.llm.backends.doubao import DoubaoLLMBackend
from memu.llm.backends.openai import OpenAILLMBackend

logger = logging.getLogger(__name__)

LLM_BACKENDS: dict[str, Callable[[], LLMBackend]] = {
    OpenAILLMBackend.name: OpenAILLMBackend,
    DoubaoLLMBackend.name: DoubaoLLMBackend,
}


class HTTPLLMClient:
    """HTTP client for LLM APIs (chat, vision, transcription)."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        chat_model: str,
        provider: str = "openai",
        endpoint_overrides: dict[str, str] | None = None,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        overrides = endpoint_overrides or {}
        self.summary_endpoint = overrides.get("chat") or overrides.get("summary") or self.backend.summary_endpoint
        self.timeout = timeout

    async def summarize(self, text: str, max_tokens: int | None = None, system_prompt: str | None = None) -> str:
        payload = self.backend.build_summary_payload(
            text=text, system_prompt=system_prompt, chat_model=self.chat_model, max_tokens=max_tokens
        )
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM summarize response: %s", data)
        return self.backend.parse_summary_response(data)

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Call Vision API with an image.

        Args:
            prompt: Text prompt to send with the image
            image_path: Path to the image file
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            LLM response text
        """
        # Read and encode image as base64
        image_data = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Detect image format
        suffix = Path(image_path).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(suffix, "image/jpeg")

        payload = self.backend.build_vision_payload(
            prompt=prompt,
            base64_image=base64_image,
            mime_type=mime_type,
            system_prompt=system_prompt,
            chat_model=self.chat_model,
            max_tokens=max_tokens,
        )

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(self.summary_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP LLM vision response: %s", data)
        return self.backend.parse_summary_response(data)

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: str = "text",
    ) -> str:
        """
        Transcribe audio file using OpenAI Audio API.

        Args:
            audio_path: Path to the audio file
            prompt: Optional prompt to guide the transcription
            language: Optional language code (e.g., 'en', 'zh')
            response_format: Response format ('text', 'json', 'verbose_json')

        Returns:
            Transcribed text
        """
        try:
            # Prepare multipart form data
            with open(audio_path, "rb") as audio_file:
                files = {"file": (Path(audio_path).name, audio_file, "application/octet-stream")}
                data = {
                    "model": "gpt-4o-mini-transcribe",
                    "response_format": response_format,
                }
                if prompt:
                    data["prompt"] = prompt
                if language:
                    data["language"] = language

                async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout * 3) as client:
                    resp = await client.post(
                        "/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()

                    if response_format == "text":
                        result = resp.text
                    else:
                        result_data = resp.json()
                        result = result_data.get("text", "")

            logger.debug("HTTP audio transcribe response for %s: %s chars", audio_path, len(result))
        except Exception:
            logger.exception("Audio transcription failed for %s", audio_path)
            raise
        else:
            return result or ""

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _load_backend(self, provider: str) -> LLMBackend:
        factory = LLM_BACKENDS.get(provider)
        if not factory:
            msg = f"Unsupported LLM provider '{provider}'. Available: {', '.join(LLM_BACKENDS.keys())}"
            raise ValueError(msg)
        return factory()
