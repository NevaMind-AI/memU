"""Shared types and helpers for vision-language model (VLM) clients.

VLM clients expose a single multimodal capability, :meth:`VLMClient.vision`,
which analyzes an image alongside a text prompt. Each transport (official SDK or
raw HTTP) implements this surface so it can be wrapped/swapped like the text LLM
clients under :mod:`memu.llm`.
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


def encode_image(image_path: str) -> tuple[str, str]:
    """Read an image and return its base64 payload and detected MIME type."""
    image_data = Path(image_path).read_bytes()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    mime_type = _MIME_BY_SUFFIX.get(Path(image_path).suffix.lower(), "image/jpeg")
    return base64_image, mime_type


class VLMClient:
    """Base interface for vision-language model clients."""

    vlm_model: str

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
