from __future__ import annotations

import base64
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from memu.vlm.backends.base import VLMBackend
from memu.vlm.backends.claude import ClaudeVLMBackend
from memu.vlm.backends.doubao import DoubaoVLMBackend
from memu.vlm.backends.grok import GrokVLMBackend
from memu.vlm.backends.kimi import KimiVLMBackend
from memu.vlm.backends.minimax import MiniMaxVLMBackend
from memu.vlm.backends.openai import OpenAIVLMBackend
from memu.vlm.backends.openrouter import OpenRouterVLMBackend
from memu.vlm.base import VLMClient, encode_image, video_mime_type

logger = logging.getLogger(__name__)

# Native video understanding processes far more data than a single image, so it
# needs a more generous read timeout than the default image-vision call.
_VIDEO_TIMEOUT_SECONDS = 240


def _load_proxy() -> str | None:
    return os.getenv("MEMU_HTTP_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or None


VLM_BACKENDS: dict[str, Callable[[], VLMBackend]] = {
    OpenAIVLMBackend.name: OpenAIVLMBackend,
    ClaudeVLMBackend.name: ClaudeVLMBackend,
    GrokVLMBackend.name: GrokVLMBackend,
    KimiVLMBackend.name: KimiVLMBackend,
    MiniMaxVLMBackend.name: MiniMaxVLMBackend,
    DoubaoVLMBackend.name: DoubaoVLMBackend,
    OpenRouterVLMBackend.name: OpenRouterVLMBackend,
}


class HTTPVLMClient(VLMClient):
    """HTTP client for vision-language model APIs (multimodal ``vision`` only)."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        vlm_model: str,
        provider: str = "openai",
        endpoint_overrides: dict[str, str] | None = None,
        timeout: int = 60,
    ):
        # Ensure base_url ends with "/" so httpx doesn't discard the path
        # component when joining with endpoint paths.
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key or ""
        self.vlm_model = vlm_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        overrides = endpoint_overrides or {}
        raw_vision_ep = overrides.get("vision") or overrides.get("chat") or self.backend.vision_endpoint
        # Strip leading "/" so httpx resolves it relative to base_url.
        self.vision_endpoint = raw_vision_ep.lstrip("/")
        raw_video_ep = overrides.get("video") or overrides.get("chat") or self.backend.video_endpoint
        self.video_endpoint = raw_video_ep.lstrip("/")
        # Surface the backend's native-video capability so callers (e.g. the
        # video preprocessor) can choose whole-video analysis over frame sampling.
        self.supports_video = self.backend.supports_video
        self.timeout = timeout
        self.proxy = _load_proxy()

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        base64_image, mime_type = encode_image(image_path)
        payload = self.backend.build_vision_payload(
            prompt=prompt,
            base64_image=base64_image,
            mime_type=mime_type,
            system_prompt=system_prompt,
            vlm_model=self.vlm_model,
            max_tokens=max_tokens,
        )
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, proxy=self.proxy) as client:
            resp = await client.post(self.vision_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP VLM vision response: %s", data)
        return self.backend.parse_vision_response(data), data

    async def video(
        self,
        prompt: str,
        video_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if not self.backend.supports_video:
            msg = f"VLM provider '{self.provider}' does not support native video understanding."
            raise NotImplementedError(msg)

        data_uri = self._encode_video_data_uri(video_path)
        payload = self.backend.build_video_payload(
            prompt=prompt,
            video_data_uri=data_uri,
            system_prompt=system_prompt,
            vlm_model=self.vlm_model,
            max_tokens=max_tokens,
        )
        timeout = max(self.timeout, _VIDEO_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout, proxy=self.proxy) as client:
            resp = await client.post(self.video_endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        logger.debug("HTTP VLM video response: %s", data)
        return self.backend.parse_video_response(data), data

    @staticmethod
    def _encode_video_data_uri(video_path: str) -> str:
        raw = Path(video_path).read_bytes()
        encoded = base64.b64encode(raw).decode("utf-8")
        return f"data:{video_mime_type(video_path)};base64,{encoded}"

    def _headers(self) -> dict[str, str]:
        return self.backend.default_headers(self.api_key)

    def _load_backend(self, provider: str) -> VLMBackend:
        factory = VLM_BACKENDS.get(provider)
        if not factory:
            msg = f"Unsupported VLM provider '{provider}'. Available: {', '.join(VLM_BACKENDS.keys())}"
            raise ValueError(msg)
        return factory()
