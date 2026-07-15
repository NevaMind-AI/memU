"""Embedding gateway: select and build a transport-specific embedding client.

Adding a new embedding transport means registering a builder in
``EMBEDDING_CLIENT_BUILDERS`` here rather than editing the service composition
root.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.app.settings import EmbeddingConfig


def _build_sdk_client(cfg: EmbeddingConfig) -> Any:
    from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient

    return OpenAIEmbeddingSDKClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        embed_model=cfg.embed_model,
        batch_size=cfg.embed_batch_size,
    )


def _build_httpx_client(cfg: EmbeddingConfig) -> Any:
    from memu.embedding.http_client import HTTPEmbeddingClient

    return HTTPEmbeddingClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        embed_model=cfg.embed_model,
        provider=cfg.provider,
        endpoint_overrides=cfg.endpoint_overrides,
    )


# Registry mapping ``client_backend`` identifiers to embedding client builders.
EMBEDDING_CLIENT_BUILDERS: dict[str, Callable[[EmbeddingConfig], Any]] = {
    "sdk": _build_sdk_client,
    "httpx": _build_httpx_client,
}


def build_embedding_client(cfg: EmbeddingConfig) -> Any:
    """Build an embedding client for ``cfg.client_backend``.

    Raises:
        ValueError: if ``cfg.client_backend`` is not registered.
    """
    builder = EMBEDDING_CLIENT_BUILDERS.get(cfg.client_backend)
    if builder is None:
        available = ", ".join(sorted(EMBEDDING_CLIENT_BUILDERS))
        msg = f"Unknown embedding client_backend '{cfg.client_backend}'. Available: {available}"
        raise ValueError(msg)
    return builder(cfg)
