"""Loopback targets must never be routed through a proxy.

A proxy sits on another host, where "localhost" means the proxy itself, not the
caller — so a proxied request to a local embedding server (Ollama & co.) can
only fail. Hosts that force all traffic through a proxy (Codex's sandbox,
corporate CI) hit this as a 502 from ``doctor`` unless the user hand-writes a
``NO_PROXY`` exemption. These pin the automatic bypass instead.
"""

from __future__ import annotations

import pytest

from memu.embedding.http_client import HTTPEmbeddingClient, _load_proxy, is_loopback_url
from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient

PROXY = "http://proxy.corp:8080"


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


def test_env_proxy_is_ignored_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    assert _load_proxy("http://localhost:11434/v1") is None
    assert _load_proxy("https://api.openai.com/v1") == PROXY


def test_http_client_bypasses_proxy_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    local = HTTPEmbeddingClient(base_url="http://localhost:11434/v1", api_key="x", embed_model="m")
    assert local.proxy is None
    assert local.trust_env is False, "httpx falls back to env proxies even with proxy=None"

    remote = HTTPEmbeddingClient(base_url="https://api.openai.com/v1", api_key="x", embed_model="m")
    assert remote.proxy == PROXY
    assert remote.trust_env is True


def test_sdk_client_bypasses_proxy_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    local = OpenAIEmbeddingSDKClient(base_url="http://localhost:11434/v1", api_key="x", embed_model="m")
    assert local.client._client.trust_env is False

    remote = OpenAIEmbeddingSDKClient(base_url="https://api.openai.com/v1", api_key="x", embed_model="m")
    assert remote.client._client.trust_env is True
