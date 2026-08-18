from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import urllib.parse
from collections.abc import Callable
from typing import Any, Literal

import httpx

from memu.embedding.backends.base import EmbeddingBackend
from memu.embedding.backends.doubao import DoubaoEmbeddingBackend, DoubaoMultimodalEmbeddingInput
from memu.embedding.backends.jina import JinaEmbeddingBackend
from memu.embedding.backends.openai import OpenAIEmbeddingBackend
from memu.embedding.backends.openrouter import OpenRouterEmbeddingBackend
from memu.embedding.backends.voyage import VoyageEmbeddingBackend
from memu.retry import DEFAULT_MAX_ATTEMPTS, RETRYABLE_STATUS_CODES, retry_delay


def is_loopback_url(url: str) -> bool:
    """True when ``url`` targets the local machine (``localhost``, ``127.x``, ``::1``).

    A request to the machine itself must never be routed through a proxy: the
    proxy sits on another host, where "localhost" means the proxy, not the
    caller. Sandboxed hosts that force all traffic through a proxy (Codex's
    sandbox, corporate CI) would otherwise turn every local-embedding-server
    call into a 502 unless the user hand-writes a ``NO_PROXY`` exemption.
    """
    host = urllib.parse.urlsplit(url).hostname or ""
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def proxy_bypass_mounts(url: str) -> dict[str, httpx.AsyncBaseTransport | None] | None:
    """httpx ``mounts`` that exempt a loopback target from env proxies, else ``None``.

    httpx gives scheme-specific env-proxy mounts (``HTTP_PROXY`` mounts on
    ``http://``) priority over a generic ``all://`` unmount, so the bypass must
    be *host*-specific — more specific than any env mount. Unmounting (rather
    than ``trust_env=False``) keeps the rest of the environment —
    ``SSL_CERT_FILE``, ``.netrc``, the user's own ``NO_PROXY`` — working.
    """
    if not is_loopback_url(url):
        return None
    host = urllib.parse.urlsplit(url).hostname or ""
    if ":" in host:  # IPv6 literal needs its brackets back
        host = f"[{host}]"
    return {f"all://{host}": None}


def _load_proxy(base_url: str) -> str | None:
    from memu.env import env as memu_env

    explicit = memu_env("MEMU_HTTP_PROXY") or None
    if is_loopback_url(base_url):
        # Ambient proxies (HTTP_PROXY, HTTPS_PROXY) are aimed at the network at
        # large, never at the machine itself. An explicit MEMU_HTTP_PROXY is
        # different — it states intent about memU's own traffic (e.g. capturing
        # it with a local debugging proxy) — so it still wins.
        return explicit
    return explicit or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or None


logger = logging.getLogger(__name__)

# The retry loop always returns or raises on its final attempt; this only exists
# so the fall-through is a loud failure rather than an implicit ``None``.
_UNREACHABLE_RETRY = "embedding retry loop exited without a response"

# Providers with a non-OpenAI endpoint/payload are registered explicitly; any
# other provider is treated as OpenAI-compatible (see ``_load_backend``).
EMBEDDING_BACKENDS: dict[str, Callable[[], EmbeddingBackend]] = {
    OpenAIEmbeddingBackend.name: OpenAIEmbeddingBackend,
    DoubaoEmbeddingBackend.name: DoubaoEmbeddingBackend,
    JinaEmbeddingBackend.name: JinaEmbeddingBackend,
    VoyageEmbeddingBackend.name: VoyageEmbeddingBackend,
    OpenRouterEmbeddingBackend.name: OpenRouterEmbeddingBackend,
}


class HTTPEmbeddingClient:
    """HTTP client for embedding APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        embed_model: str,
        provider: str = "openai",
        endpoint_overrides: dict[str, str] | None = None,
        timeout: int = 60,
        embed_batch_size: int = 64,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ):
        # Ensure base_url ends with "/" so httpx doesn't discard the path
        # component when joining with endpoint paths.
        # See: https://github.com/NevaMind-AI/memU/issues/328
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key or ""
        self.embed_model = embed_model
        self.provider = provider.lower()
        self.backend = self._load_backend(self.provider)
        overrides = endpoint_overrides or {}
        raw_embedding_ep = (
            overrides.get("embeddings")
            or overrides.get("embedding")
            or overrides.get("embed")
            or self.backend.embedding_endpoint
        )
        # Strip leading "/" so httpx resolves relative to base_url
        self.embedding_endpoint = raw_embedding_ep.lstrip("/")
        self.timeout = timeout
        self.embed_batch_size = max(1, embed_batch_size)
        self.max_attempts = max(1, max_attempts)
        self.proxy = _load_proxy(self.base_url)
        # httpx falls back to env proxies even when proxy=None, so a loopback
        # target explicitly unmounts them (host-specifically — see
        # proxy_bypass_mounts). An explicit MEMU_HTTP_PROXY means self.proxy is
        # set and no bypass applies.
        self.mounts = proxy_bypass_mounts(self.base_url) if self.proxy is None else None

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        """
        Create text embeddings.

        Args:
            inputs: List of text strings to embed

        Returns:
            Tuple of (list of embedding vectors, raw response dict). The raw
            response carries provider ``usage`` so callers/interceptors can
            track token consumption. Inputs beyond ``embed_batch_size`` are sent
            as several sequential requests, in which case only the last raw
            response is returned (the same contract as the SDK client).
        """
        if not inputs:
            return [], {}

        vectors: list[list[float]] = []
        data: dict[str, Any] = {}
        # One client for every batch: each request otherwise pays its own TLS
        # handshake, which on a many-segment commit dominates the wall clock.
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, proxy=self.proxy, mounts=self.mounts
        ) as client:
            for start in range(0, len(inputs), self.embed_batch_size):
                batch = inputs[start : start + self.embed_batch_size]
                data = await self._post_embeddings(client, batch)
                logger.debug("HTTP embedding response: %s", data)
                vectors.extend(self.backend.parse_embedding_response(data))
        return vectors, data

    async def _post_embeddings(self, client: httpx.AsyncClient, batch: list[str]) -> dict[str, Any]:
        """POST one batch, retrying the failures a retry can actually fix.

        Rate limits and provider 5xx are transient by nature, and an embedding
        call sits on the critical path of a commit that has already done work —
        letting a single 429 abort the whole thing wastes every embedding
        already paid for. Terminal failures (401, unknown model) still surface
        on the first attempt via ``raise_for_status``.
        """
        payload = self.backend.build_embedding_payload(inputs=batch, embed_model=self.embed_model)
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = await client.post(self.embedding_endpoint, json=payload, headers=self._headers())
            except httpx.TransportError:
                # Connection resets, DNS failures and timeouts alike
                # (TimeoutException is a TransportError).
                if attempt == self.max_attempts:
                    raise
                await asyncio.sleep(retry_delay(attempt))
                continue
            if resp.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_attempts:
                logger.debug("embedding request returned %s; retry %s/%s", resp.status_code, attempt, self.max_attempts)
                await asyncio.sleep(retry_delay(attempt, resp))
                continue
            # The last attempt falls through here whatever its status, so an
            # exhausted retry still raises the provider's real error.
            resp.raise_for_status()
            json_data: dict[str, Any] = resp.json()
            return json_data
        raise AssertionError(_UNREACHABLE_RETRY)

    async def embed_multimodal(
        self,
        inputs: list[tuple[Literal["text", "image_url", "video_url"], str]],
        *,
        encoding_format: str = "float",
    ) -> list[list[float]]:
        """
        Create multimodal embeddings using Doubao embedding vision API.

        This method supports embedding a mix of text, images, and videos in a single request.
        Only available when using the 'doubao' provider.

        Args:
            inputs: List of tuples where each tuple contains:
                - input_type: One of 'text', 'image_url', or 'video_url'
                - content: The text content or URL to the image/video
            encoding_format: Encoding format for the embeddings ('float' or 'base64')

        Returns:
            List of embedding vectors

        Example:
            >>> client = HTTPEmbeddingClient(
            ...     base_url="https://ark.cn-beijing.volces.com",
            ...     api_key="your-api-key",
            ...     embed_model="doubao-embedding-vision-250615",
            ...     provider="doubao",
            ... )
            >>> embeddings = await client.embed_multimodal([
            ...     ("text", "What is in the image and video?"),
            ...     ("image_url", "https://example.com/image.png"),
            ...     ("video_url", "https://example.com/video.mp4"),
            ... ])

        Raises:
            TypeError: If the backend does not support multimodal embeddings
        """
        if not isinstance(self.backend, DoubaoEmbeddingBackend):
            msg = (
                f"Multimodal embedding is only supported by 'doubao' provider, "
                f"but current provider is '{self.provider}'"
            )
            raise TypeError(msg)

        multimodal_inputs = [
            DoubaoMultimodalEmbeddingInput(input_type=input_type, content=content) for input_type, content in inputs
        ]

        payload = self.backend.build_multimodal_embedding_payload(
            inputs=multimodal_inputs,
            embed_model=self.embed_model,
            encoding_format=encoding_format,
        )

        endpoint = self.backend.multimodal_embedding_endpoint.lstrip("/")
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, proxy=self.proxy, mounts=self.mounts
        ) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        logger.debug("HTTP multimodal embedding response: %s", data)
        return self.backend.parse_multimodal_embedding_response(data)

    def _headers(self) -> dict[str, str]:
        return self.backend.default_headers(self.api_key)

    def _load_backend(self, provider: str) -> EmbeddingBackend:
        # Providers with a non-standard endpoint/payload are registered
        # explicitly; everything else is treated as OpenAI-compatible (the most
        # common case, e.g. grok/deepseek/kimi/minimax).
        factory = EMBEDDING_BACKENDS.get(provider, OpenAIEmbeddingBackend)
        return factory()
