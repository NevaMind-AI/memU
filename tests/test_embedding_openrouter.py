"""Exercise OpenRouter config through the real SDK and HTTPX request builders."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from memu.app.settings import EmbeddingConfig
from memu.embedding.gateway import build_embedding_client
from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient
from memu.env import embedding_profile


@pytest.fixture
def embedding_peer(monkeypatch, tmp_path):
    requests = []

    class Peer(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, payload, self.headers["Authorization"]))
            self.send_response(200)  # Measure the actual URL; accept every path.
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    "object": "list",
                    "model": payload["model"],
                    "data": [{"object": "embedding", "index": 0, "embedding": [1.0, 0.0]}],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                }).encode()
            )

    monkeypatch.setenv("MEMU_CONFIG_ENV", str(tmp_path / "unused.env"))
    monkeypatch.setenv("MEMU_HTTP_PROXY", "")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    with ThreadingHTTPServer(("127.0.0.1", 0), Peer) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", requests
        finally:
            server.shutdown()
            thread.join()


@pytest.mark.parametrize(
    ("options", "base_url", "path"),
    [
        ({}, "https://openrouter.ai/api/v1", "/api/v1/embeddings"),
        ({"client_backend": "sdk"}, "https://openrouter.ai/api/v1", "/api/v1/embeddings"),
        ({"client_backend": "httpx"}, "https://openrouter.ai", "/api/v1/embeddings"),
        ({"base_url": "https://openrouter.ai"}, "https://openrouter.ai", "/embeddings"),
        ({"base_url": "https://proxy.example/custom/v1/"}, "https://proxy.example/custom/v1/", "/custom/v1/embeddings"),
        ({"base_url": "https://openrouter.ai/api/v1"}, "https://openrouter.ai/api/v1", "/api/v1/embeddings"),
        (
            {"client_backend": "httpx", "base_url": "https://proxy.example/prefix"},
            "https://proxy.example/prefix",
            "/prefix/api/v1/embeddings",
        ),
        (
            {
                "client_backend": "httpx",
                "base_url": "https://proxy.example/v1",
                "endpoint_overrides": {"embeddings": "/vectors"},
            },
            "https://proxy.example/v1",
            "/v1/vectors",
        ),
    ],
)
async def test_openrouter_request_path(embedding_peer, options, base_url, path):
    origin, requests = embedding_peer
    cfg = EmbeddingConfig(provider="openrouter", api_key="local-fixture", **options)
    configured_base_url = cfg.base_url
    assert cfg.embed_model == "openai/text-embedding-3-small"
    # Preserve the configured URL path while redirecting only the origin locally.
    cfg.base_url = origin + urlsplit(cfg.base_url).path
    client = build_embedding_client(cfg)
    try:
        vectors, _ = await client.embed(["hello"])
    finally:
        if isinstance(client, OpenAIEmbeddingSDKClient):
            await client.client.close()
    assert vectors == [[1.0, 0.0]]
    assert len(requests) == 1
    actual_path, payload, authorization = requests[0]
    assert actual_path == path
    assert configured_base_url == base_url
    assert payload["input"] == ["hello"]
    assert payload["model"] == cfg.embed_model
    assert authorization == "Bearer local-fixture"


def test_openrouter_environment_profile_uses_sdk_default(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(tmp_path / "unused.env"))
    monkeypatch.setenv("MEMU_EMBED_PROVIDER", "openrouter")
    for name in ("MEMU_BASE_URL", "MEMU_EMBED_MODEL", "MEMU_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    cfg = EmbeddingConfig(**embedding_profile())
    assert cfg.client_backend == "sdk"
    assert cfg.base_url == "https://openrouter.ai/api/v1"
    assert cfg.api_key == "OPENROUTER_API_KEY"
