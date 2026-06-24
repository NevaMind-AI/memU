"""LLM gateway: select and build a transport-specific LLM client.

This module centralizes the dispatch from configuration (``LLMConfig``) to a
concrete client implementation under :mod:`memu.llm`. Adding a new LLM
implementation means registering a builder in ``LLM_CLIENT_BUILDERS`` here rather
than editing the service composition root.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.settings import LLMConfig


def _build_sdk_client(cfg: LLMConfig) -> Any:
    from memu.llm.openai_client import OpenAIClient

    return OpenAIClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        chat_model=cfg.chat_model,
    )


def _build_anthropic_client(cfg: LLMConfig) -> Any:
    from memu.llm.anthropic_client import AnthropicClient

    # The OpenAI default base_url is meaningless for Anthropic; let the SDK use
    # its own default (https://api.anthropic.com) unless explicitly overridden.
    base_url = None if cfg.base_url == "https://api.openai.com/v1" else cfg.base_url
    return AnthropicClient(
        base_url=base_url,
        api_key=cfg.api_key,
        chat_model=cfg.chat_model,
    )


def _build_httpx_client(cfg: LLMConfig) -> Any:
    from memu.llm.http_client import HTTPLLMClient

    return HTTPLLMClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        chat_model=cfg.chat_model,
        provider=cfg.provider,
        endpoint_overrides=cfg.endpoint_overrides,
    )


def _build_lazyllm_client(cfg: LLMConfig) -> Any:
    from memu.llm.lazyllm_client import LazyLLMClient

    source = cfg.lazyllm_source
    return LazyLLMClient(
        llm_source=source.llm_source or source.source,
        vlm_source=source.vlm_source or source.source,
        embed_source=source.embed_source or source.source,
        stt_source=source.stt_source or source.source,
        chat_model=cfg.chat_model,
        embed_model=cfg.embed_model,
        vlm_model=source.vlm_model,
        stt_model=source.stt_model,
    )


# Registry mapping ``client_backend`` identifiers to client builders. Register
# new LLM implementations here.
LLM_CLIENT_BUILDERS: dict[str, Callable[[LLMConfig], Any]] = {
    "sdk": _build_sdk_client,
    "anthropic": _build_anthropic_client,
    "httpx": _build_httpx_client,
    "lazyllm_backend": _build_lazyllm_client,
}


def build_llm_client(cfg: LLMConfig) -> Any:
    """Build an LLM client for ``cfg.client_backend``.

    Raises:
        ValueError: if ``cfg.client_backend`` is not registered.
    """
    builder = LLM_CLIENT_BUILDERS.get(cfg.client_backend)
    if builder is None:
        available = ", ".join(sorted(LLM_CLIENT_BUILDERS))
        msg = f"Unknown llm_client_backend '{cfg.client_backend}'. Available: {available}"
        raise ValueError(msg)
    return builder(cfg)
