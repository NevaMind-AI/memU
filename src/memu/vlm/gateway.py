"""VLM gateway: select and build a transport-specific vision-language client.

Mirrors :mod:`memu.llm.gateway`. Adding a new VLM transport means registering a
builder in ``VLM_CLIENT_BUILDERS`` here rather than editing the service
composition root.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.settings import VLMConfig


def _build_sdk_client(cfg: VLMConfig) -> Any:
    from memu.vlm.openai_client import OpenAIVLMClient

    return OpenAIVLMClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        vlm_model=cfg.vlm_model,
    )


def _build_anthropic_client(cfg: VLMConfig) -> Any:
    from memu.vlm.anthropic_client import AnthropicVLMClient

    # The OpenAI default base_url is meaningless for Anthropic; let the SDK use
    # its own default (https://api.anthropic.com) unless explicitly overridden.
    base_url = None if cfg.base_url == "https://api.openai.com/v1" else cfg.base_url
    return AnthropicVLMClient(
        base_url=base_url,
        api_key=cfg.api_key,
        vlm_model=cfg.vlm_model,
    )


def _build_httpx_client(cfg: VLMConfig) -> Any:
    from memu.vlm.http_client import HTTPVLMClient

    return HTTPVLMClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        vlm_model=cfg.vlm_model,
        provider=cfg.provider,
        endpoint_overrides=cfg.endpoint_overrides,
    )


# Registry mapping ``client_backend`` identifiers to VLM client builders.
VLM_CLIENT_BUILDERS: dict[str, Callable[[VLMConfig], Any]] = {
    "sdk": _build_sdk_client,
    "anthropic": _build_anthropic_client,
    "httpx": _build_httpx_client,
}


def build_vlm_client(cfg: VLMConfig) -> Any:
    """Build a VLM client for ``cfg.client_backend``.

    Raises:
        ValueError: if ``cfg.client_backend`` is not registered.
    """
    builder = VLM_CLIENT_BUILDERS.get(cfg.client_backend)
    if builder is None:
        available = ", ".join(sorted(VLM_CLIENT_BUILDERS))
        msg = f"Unknown vlm_client_backend '{cfg.client_backend}'. Available: {available}"
        raise ValueError(msg)
    return builder(cfg)
