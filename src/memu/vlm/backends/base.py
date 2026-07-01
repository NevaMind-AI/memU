from __future__ import annotations

from typing import Any, ClassVar


class VLMBackend:
    """Defines how to talk to a specific HTTP vision-language model provider.

    Mirrors :class:`memu.llm.backends.base.LLMBackend` but is scoped to the
    multimodal ``vision`` capability: each provider lives in its own module under
    :mod:`memu.vlm.backends` and customizes the request endpoint, vision payload
    shape, response parsing and (when needed) the auth headers.
    """

    name: str = "base"
    vision_endpoint: str = "/chat/completions"
    video_endpoint: str = "/chat/completions"

    # Whether this provider can analyze a whole video file natively (frames +
    # audio) via :meth:`build_video_payload`. Providers without native video
    # understanding leave this ``False`` so callers fall back to frame-based
    # image analysis instead.
    supports_video: ClassVar[bool] = False

    def default_headers(self, api_key: str) -> dict[str, str]:
        """Auth/request headers for this provider.

        Defaults to OpenAI-style bearer auth; providers with a different scheme
        (e.g. Anthropic's ``x-api-key``) override this.
        """
        return {"Authorization": f"Bearer {api_key}"}

    def build_vision_payload(
        self,
        *,
        prompt: str,
        base64_image: str,
        mime_type: str,
        system_prompt: str | None,
        vlm_model: str,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def parse_vision_response(self, data: dict[str, Any]) -> str:
        raise NotImplementedError

    def build_video_payload(
        self,
        *,
        prompt: str,
        video_data_uri: str,
        system_prompt: str | None,
        vlm_model: str,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        """Build the request payload for native whole-video understanding.

        Only meaningful when :attr:`supports_video` is ``True``.
        """
        raise NotImplementedError

    def parse_video_response(self, data: dict[str, Any]) -> str:
        """Parse a native video response (defaults to the vision parser)."""
        return self.parse_vision_response(data)
