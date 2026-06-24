"""Unit tests for the standalone ``memu.embedding`` package.

These pin the embedding module's contract that mirrors ``memu.llm``/``memu.vlm``:

- per-provider backends (openai/jina/voyage/openrouter/doubao) build the right
  payload/endpoint and parse the ``data[].embedding`` response shape.
- the HTTP client falls back to an OpenAI-compatible backend for unknown
  providers and returns ``(vectors, raw_response)``.
- the gateway dispatches on ``client_backend`` and raises clearly for anthropic.
- ``EmbeddingConfig`` resolves per-provider base_url/api_key/model defaults, and
  ``embedding_config_from_llm`` derives a config from an LLM profile.
"""

from __future__ import annotations

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest  # noqa: E402

from memu.app.settings import EmbeddingConfig, LLMConfig, embedding_config_from_llm  # noqa: E402
from memu.embedding.backends import (  # noqa: E402
    JinaEmbeddingBackend,
    OpenAIEmbeddingBackend,
    OpenRouterEmbeddingBackend,
    VoyageEmbeddingBackend,
)
from memu.embedding.gateway import build_embedding_client  # noqa: E402
from memu.embedding.http_client import HTTPEmbeddingClient  # noqa: E402
from memu.embedding.openai_sdk import OpenAIEmbeddingSDKClient  # noqa: E402


@pytest.mark.parametrize(
    ("backend", "endpoint"),
    [
        (OpenAIEmbeddingBackend(), "/embeddings"),
        (JinaEmbeddingBackend(), "/embeddings"),
        (VoyageEmbeddingBackend(), "/embeddings"),
        (OpenRouterEmbeddingBackend(), "/api/v1/embeddings"),
    ],
)
def test_backend_payload_and_parse(backend, endpoint):
    assert backend.embedding_endpoint == endpoint
    assert backend.default_headers("k") == {"Authorization": "Bearer k"}

    payload = backend.build_embedding_payload(inputs=["a", "b"], embed_model="m")
    assert payload["model"] == "m"
    assert payload["input"] == ["a", "b"]

    parsed = backend.parse_embedding_response({"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})
    assert parsed == [[0.1, 0.2], [0.3, 0.4]]


def test_http_client_unknown_provider_falls_back_to_openai():
    client = HTTPEmbeddingClient(base_url="https://x/v1", api_key="k", embed_model="m", provider="grok")
    assert isinstance(client.backend, OpenAIEmbeddingBackend)


def test_http_client_selects_registered_backend():
    client = HTTPEmbeddingClient(base_url="https://api.jina.ai/v1", api_key="k", embed_model="m", provider="jina")
    assert isinstance(client.backend, JinaEmbeddingBackend)


async def test_http_client_embed_returns_vectors_and_raw(monkeypatch):
    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"embedding": [1.0, 2.0]}], "usage": {"total_tokens": 3}}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, endpoint, json, headers):
            captured["endpoint"] = endpoint
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse()

    import memu.embedding.http_client as http_mod

    monkeypatch.setattr(http_mod.httpx, "AsyncClient", _FakeAsyncClient)

    client = HTTPEmbeddingClient(
        base_url="https://api.voyageai.com/v1", api_key="key", embed_model="voyage-3.5", provider="voyage"
    )
    vectors, raw = await client.embed(["hello"])

    assert vectors == [[1.0, 2.0]]
    assert raw["usage"]["total_tokens"] == 3
    assert captured["endpoint"] == "embeddings"  # leading slash stripped
    assert captured["headers"] == {"Authorization": "Bearer key"}
    assert captured["json"] == {"model": "voyage-3.5", "input": ["hello"]}


def test_gateway_builds_sdk_and_httpx_clients():
    sdk = build_embedding_client(EmbeddingConfig(provider="openai", api_key="k", client_backend="sdk"))
    assert isinstance(sdk, OpenAIEmbeddingSDKClient)

    httpx_client = build_embedding_client(EmbeddingConfig(provider="jina", api_key="k", client_backend="httpx"))
    assert isinstance(httpx_client, HTTPEmbeddingClient)
    assert isinstance(httpx_client.backend, JinaEmbeddingBackend)


def test_gateway_rejects_anthropic_and_unknown_backends():
    with pytest.raises(ValueError, match="Anthropic does not provide"):
        build_embedding_client(EmbeddingConfig(client_backend="anthropic"))

    with pytest.raises(ValueError, match="Unknown embedding client_backend"):
        build_embedding_client(EmbeddingConfig(client_backend="nope"))


def test_embedding_config_provider_defaults():
    jina = EmbeddingConfig(provider="jina")
    assert jina.base_url == "https://api.jina.ai/v1"
    assert jina.api_key == "JINA_API_KEY"
    assert jina.embed_model == "jina-embeddings-v3"

    voyage = EmbeddingConfig(provider="voyage")
    assert voyage.base_url == "https://api.voyageai.com/v1"
    assert voyage.api_key == "VOYAGE_API_KEY"
    assert voyage.embed_model == "voyage-3.5"

    # Explicit values always survive the provider-default merge.
    explicit = EmbeddingConfig(provider="jina", base_url="https://proxy/v1", api_key="real", embed_model="custom")
    assert explicit.base_url == "https://proxy/v1"
    assert explicit.api_key == "real"
    assert explicit.embed_model == "custom"


def test_chat_clients_no_longer_expose_embed():
    """Embedding is fully decoupled: text/chat clients must not carry embed()."""
    from memu.llm.anthropic_client import AnthropicClient
    from memu.llm.http_client import HTTPLLMClient
    from memu.llm.openai_client import OpenAIClient

    assert not hasattr(OpenAIClient, "embed")
    assert not hasattr(HTTPLLMClient, "embed")
    assert not hasattr(AnthropicClient, "embed")
    # The HTTP chat client no longer wires an embedding backend either.
    assert not hasattr(HTTPLLMClient, "_load_embedding_backend")


def test_embedding_config_from_llm_carries_transport_and_model():
    llm = LLMConfig(
        provider="openrouter",
        client_backend="httpx",
        api_key="rk",
        embed_model="openai/text-embedding-3-large",
    )
    emb = embedding_config_from_llm(llm)
    assert emb.provider == "openrouter"
    assert emb.client_backend == "httpx"
    assert emb.api_key == "rk"
    assert emb.embed_model == "openai/text-embedding-3-large"
    assert emb.base_url == llm.base_url
