"""Shared types and helpers for vision-language model (VLM) clients.

VLM clients expose multimodal understanding capabilities: :meth:`VLMClient.vision`
analyzes an image alongside a text prompt, and the optional
:meth:`VLMClient.video` analyzes a whole video natively (when the provider
supports it). Each transport (official SDK or raw HTTP) implements this surface
so it can be wrapped/swapped like the text LLM clients under :mod:`memu.llm`.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

_VIDEO_MIME_BY_SUFFIX = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
}


def video_mime_type(video_path: str) -> str:
    """Return the MIME type for a video file based on its suffix."""
    return _VIDEO_MIME_BY_SUFFIX.get(Path(video_path).suffix.lower(), "video/mp4")


def encode_image(image_path: str) -> tuple[str, str]:
    """Read an image and return its base64 payload and detected MIME type."""
    image_data = Path(image_path).read_bytes()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    mime_type = _MIME_BY_SUFFIX.get(Path(image_path).suffix.lower(), "image/jpeg")
    return base64_image, mime_type


class VLMClient:
    """Base interface for vision-language model clients."""

    vlm_model: str

    # Whether this client can analyze a whole video file natively (audio + frames)
    # via :meth:`video`. Providers without native video understanding leave this
    # ``False`` so callers can fall back to frame-based image analysis instead.
    # Not a ``ClassVar`` because transports like :class:`HTTPVLMClient` resolve it
    # per-instance from the configured provider backend.
    supports_video: bool = False

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, Any]:
        """Analyze ``image_path`` with ``prompt`` and return ``(text, raw_response)``."""
        raise NotImplementedError

    async def video(
        self,
        prompt: str,
        video_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, Any]:
        """Analyze the whole video at ``video_path`` and return ``(text, raw_response)``.

        Only implemented by providers with native video understanding (see
        :attr:`supports_video`). The default raises :class:`NotImplementedError`.
        """
        raise NotImplementedError
