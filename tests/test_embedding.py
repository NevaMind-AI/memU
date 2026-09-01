"""Unit tests for the standalone ``memu.embedding`` package.

These pin the embedding module's contract:

- per-provider backends (openai/jina/voyage/openrouter/doubao) build the right
  payload/endpoint and parse the ``data[].embedding`` response shape.
- the HTTP client falls back to an OpenAI-compatible backend for unknown
  providers and returns ``(vectors, raw_response)``.
- the gateway dispatches on ``client_backend``.
- ``EmbeddingConfig`` resolves per-provider base_url/api_key/model defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import httpx  # noqa: E402
import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from memu.app.settings import EmbeddingConfig  # noqa: E402
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
        status_code = 200

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


async def test_http_client_splits_inputs_into_batches(monkeypatch):
    """A list longer than ``embed_batch_size`` becomes several requests, one client."""
    posted: list[list[str]] = []
    clients: list[object] = []

    class _FakeResponse:
        status_code = 200

        def __init__(self, count: int):
            self._count = count

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"embedding": [float(i)]} for i in range(self._count)]}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            clients.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, endpoint, json, headers):
            posted.append(json["input"])
            return _FakeResponse(len(json["input"]))

    import memu.embedding.http_client as http_mod

    monkeypatch.setattr(http_mod.httpx, "AsyncClient", _FakeAsyncClient)

    client = HTTPEmbeddingClient(base_url="https://x/v1", api_key="k", embed_model="m", embed_batch_size=2)
    vectors, _ = await client.embed(["a", "b", "c", "d", "e"])

    assert posted == [["a", "b"], ["c", "d"], ["e"]]
    assert len(vectors) == 5
    assert len(clients) == 1  # every batch shares one connection pool


async def test_http_client_embed_of_nothing_makes_no_request(monkeypatch):
    """An empty commit must not post an empty ``input`` the provider would reject."""

    built = False

    class _RecordingAsyncClient:
        def __init__(self, *args, **kwargs):
            nonlocal built
            built = True

    import memu.embedding.http_client as http_mod

    monkeypatch.setattr(http_mod.httpx, "AsyncClient", _RecordingAsyncClient)

    client = HTTPEmbeddingClient(base_url="https://x/v1", api_key="k", embed_model="m")
    assert await client.embed([]) == ([], {})
    assert not built


class _StubResponse:
    """Minimal httpx.Response stand-in for the retry tests."""

    def __init__(self, status_code: int, *, headers: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://x/v1/embeddings")
            raise httpx.HTTPStatusError(
                str(self.status_code),
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )

    def json(self):
        return {"data": [{"embedding": [1.0]}]}


def _client_over(responses, monkeypatch, **kwargs):
    """Build an HTTPEmbeddingClient whose POSTs replay ``responses`` in order."""
    attempts: list = []

    class _FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, endpoint, json, headers):
            outcome = responses[len(attempts)]
            attempts.append(outcome)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    import memu.embedding.http_client as http_mod

    monkeypatch.setattr(http_mod.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(http_mod.asyncio, "sleep", _no_sleep)
    return HTTPEmbeddingClient(base_url="https://x/v1", api_key="k", embed_model="m", **kwargs), attempts


async def _no_sleep(_seconds):
    return None


async def test_embed_retries_rate_limit_then_succeeds(monkeypatch):
    client, attempts = _client_over([_StubResponse(429, headers={"Retry-After": "0"}), _StubResponse(200)], monkeypatch)
    vectors, _ = await client.embed(["a"])

    assert vectors == [[1.0]]
    assert len(attempts) == 2


async def test_embed_retries_transport_errors(monkeypatch):
    client, attempts = _client_over([httpx.ConnectError("boom"), _StubResponse(200)], monkeypatch)
    vectors, _ = await client.embed(["a"])

    assert vectors == [[1.0]]
    assert len(attempts) == 2


async def test_embed_does_not_retry_terminal_failures(monkeypatch):
    """A 401 fails the same way every time; burning attempts only delays it."""
    client, attempts = _client_over([_StubResponse(401)] * 3, monkeypatch)

    with pytest.raises(httpx.HTTPStatusError):
        await client.embed(["a"])
    assert len(attempts) == 1


async def test_embed_surfaces_the_provider_error_once_retries_are_exhausted(monkeypatch):
    client, attempts = _client_over([_StubResponse(503)] * 3, monkeypatch, max_attempts=3)

    with pytest.raises(httpx.HTTPStatusError):
        await client.embed(["a"])
    assert len(attempts) == 3


def test_embed_batch_size_defaults_to_batching_and_is_plumbed_to_both_backends():
    # A default of 1 silently turned each batched call into N sequential requests.
    assert EmbeddingConfig().embed_batch_size == 64

    httpx_client = build_embedding_client(EmbeddingConfig(client_backend="httpx", embed_batch_size=8))
    assert httpx_client.embed_batch_size == 8

    sdk = build_embedding_client(EmbeddingConfig(client_backend="sdk", embed_batch_size=8))
    assert sdk.batch_size == 8

    with pytest.raises(ValidationError):
        EmbeddingConfig(embed_batch_size=0)


def test_gateway_builds_sdk_and_httpx_clients():
    sdk = build_embedding_client(EmbeddingConfig(provider="openai", api_key="k", client_backend="sdk"))
    assert isinstance(sdk, OpenAIEmbeddingSDKClient)

    httpx_client = build_embedding_client(EmbeddingConfig(provider="jina", api_key="k", client_backend="httpx"))
    assert isinstance(httpx_client, HTTPEmbeddingClient)
    assert isinstance(httpx_client.backend, JinaEmbeddingBackend)


def test_gateway_rejects_unknown_backends():
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


def test_embedding_space_tracks_model_and_endpoint_without_credentials():
    first = EmbeddingConfig(
        provider="openai",
        embed_model="model-a",
        base_url="https://alice:secret@example.test/v1?token=one",
    )
    other_credentials = EmbeddingConfig(
        provider="openai",
        embed_model="model-a",
        base_url="https://bob:different@example.test/v1?token=two",
    )
    other_model = first.model_copy(update={"embed_model": "model-b"})

    assert first.embedding_space == other_credentials.embedding_space
    assert first.embedding_space != other_model.embedding_space
    assert "secret" not in first.embedding_space
