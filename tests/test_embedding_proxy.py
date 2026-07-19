"""Loopback targets must never be routed through an ambient proxy.

A proxy sits on another host, where "localhost" means the proxy itself, not the
caller — so a proxied request to a local embedding server (Ollama & co.) can
only fail. Hosts that force all traffic through a proxy (Codex's sandbox,
corporate CI) hit this as a 502 from ``doctor`` unless the user hand-writes a
``NO_PROXY`` exemption. These pin the automatic bypass — and its deliberate
limits: an explicit ``MEMU_HTTP_PROXY`` still wins (stated intent about memU's
own traffic), and the bypass unmounts only the target host, leaving the rest of
the environment (``SSL_CERT_FILE``, ``.netrc``, the user's own ``NO_PROXY``)
trusted.
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest

from memu.embedding.http_client import HTTPEmbeddingClient, _load_proxy, is_loopback_url, proxy_bypass_mounts
from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient

PROXY = "http://proxy.corp:8080"


@pytest.fixture(autouse=True)
def _clean_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The developer's own shell may carry proxy settings (corporate machines
    usually do); these tests must not depend on them."""
    for key in list(os.environ):
        if key.lower().endswith("_proxy") or key.lower() == "no_proxy":
            monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434/v1",
        "http://LOCALHOST:11434/v1",
        "http://ollama.localhost/v1",
        "http://127.0.0.1:11434/v1",
        "http://127.5.5.5/v1",
        "http://[::1]:11434/v1",
    ],
)
def test_loopback_urls_are_recognized(url: str) -> None:
    assert is_loopback_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "http://192.168.1.23:11434/v1",
        "http://host.docker.internal:11434/v1",
        "http://localhost.evil.com/v1",
        "",
    ],
)
def test_remote_urls_are_not(url: str) -> None:
    assert not is_loopback_url(url)


def test_ambient_proxy_is_ignored_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    assert _load_proxy("http://localhost:11434/v1") is None
    assert _load_proxy("https://api.openai.com/v1") == PROXY


def test_explicit_memu_proxy_wins_even_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """MEMU_HTTP_PROXY states intent about memU's own traffic — e.g. capturing
    it with a local debugging proxy — so the loopback bypass yields to it."""
    monkeypatch.setenv("MEMU_HTTP_PROXY", PROXY)
    assert _load_proxy("http://localhost:11434/v1") == PROXY

    client = HTTPEmbeddingClient(base_url="http://localhost:11434/v1", api_key="x", embed_model="m")
    assert client.proxy == PROXY
    assert client.mounts is None


def test_bypass_mounts_are_host_specific() -> None:
    """httpx gives scheme-specific env mounts (HTTP_PROXY -> "http://") priority
    over a generic "all://" unmount — only a host pattern reliably wins."""
    assert proxy_bypass_mounts("http://localhost:11434/v1") == {"all://localhost": None}
    assert proxy_bypass_mounts("http://127.0.0.1:11434/v1") == {"all://127.0.0.1": None}
    assert proxy_bypass_mounts("http://[::1]:11434/v1") == {"all://[::1]": None}
    assert proxy_bypass_mounts("https://api.openai.com/v1") is None


def test_http_client_bypasses_ambient_proxy_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    local = HTTPEmbeddingClient(base_url="http://localhost:11434/v1", api_key="x", embed_model="m")
    assert local.proxy is None
    assert local.mounts == {"all://localhost": None}

    remote = HTTPEmbeddingClient(base_url="https://api.openai.com/v1", api_key="x", embed_model="m")
    assert remote.proxy == PROXY
    assert remote.mounts is None


def _resolved_transport(client: OpenAIEmbeddingSDKClient, url: str) -> object:
    inner = client.client._client
    return inner._transport_for_url(httpx.URL(url))


def test_sdk_client_bypasses_ambient_proxy_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    monkeypatch.setenv("HTTPS_PROXY", PROXY)  # HTTP_PROXY only covers http:// URLs
    local = OpenAIEmbeddingSDKClient(base_url="http://localhost:11434/v1", api_key="x", embed_model="m")
    assert _resolved_transport(local, "http://localhost:11434/v1/embeddings") is local.client._client._transport

    remote = OpenAIEmbeddingSDKClient(base_url="https://api.openai.com/v1", api_key="x", embed_model="m")
    assert _resolved_transport(remote, "https://api.openai.com/v1/embeddings") is not remote.client._client._transport


def test_sdk_client_honors_memu_proxy_on_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    """The escape hatch must work with no ambient proxies to hide behind —
    asserting it alongside HTTP_PROXY would be a false green (the transport
    would be non-default because of the ambient proxy, not MEMU_HTTP_PROXY)."""
    monkeypatch.setenv("MEMU_HTTP_PROXY", PROXY)
    opted_in = OpenAIEmbeddingSDKClient(base_url="http://localhost:11434/v1", api_key="x", embed_model="m")
    assert (
        _resolved_transport(opted_in, "http://localhost:11434/v1/embeddings") is not opted_in.client._client._transport
    ), "MEMU_HTTP_PROXY alone must actually reach the SDK transport"


async def _json_server(payload: dict) -> tuple[asyncio.Server, int]:
    """A real local HTTP server that answers any request with ``payload``."""
    body = json.dumps(payload).encode()
    response = (
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\nConnection: close\r\n\r\n"
        + body
    )

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = await reader.read(1024)
            if not chunk:
                break
            data += chunk
        writer.write(response)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def test_embed_reaches_local_server_despite_dead_env_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Behavioral proof: with HTTP_PROXY pointing at a dead address, a request
    to a real local server succeeds only if the proxy was bypassed."""
    server, port = await _json_server({"data": [{"embedding": [1.0, 2.0]}], "usage": {"total_tokens": 1}})
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")  # nothing listens there

    try:
        client = HTTPEmbeddingClient(base_url=f"http://127.0.0.1:{port}/v1", api_key="x", embed_model="m")
        vectors, raw = await client.embed(["hi"])
    finally:
        server.close()
        await server.wait_closed()

    assert vectors == [[1.0, 2.0]]
    assert raw["usage"]["total_tokens"] == 1


async def test_sdk_embed_reaches_local_server_despite_dead_env_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same behavioral proof for the SDK path. Its other assertions resolve
    transports through httpx internals; this one rests only on observable
    behavior, so it survives httpx refactors."""
    server, port = await _json_server({
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": [3.0, 4.0]}],
        "model": "m",
        "usage": {"prompt_tokens": 1, "total_tokens": 1},
    })
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")  # nothing listens there

    try:
        client = OpenAIEmbeddingSDKClient(base_url=f"http://127.0.0.1:{port}/v1", api_key="x", embed_model="m")
        vectors, response = await client.embed(["hi"])
    finally:
        server.close()
        await server.wait_closed()

    assert vectors == [[3.0, 4.0]]
    assert response is not None and response.usage.total_tokens == 1
