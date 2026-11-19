"""Exercise Doubao response formats through the public HTTP embedding client."""

import base64
import json
import struct
from functools import partial

import httpx
import pytest

from memu.embedding.http_client import HTTPEmbeddingClient


@pytest.mark.parametrize("data_is_list", [False, True])
@pytest.mark.parametrize("encoding_format", ["float", "base64"])
async def test_multimodal_embedding_response(monkeypatch, tmp_path, data_is_list, encoding_format):
    vector = [0.25, -0.5, 1.0]
    embedding = base64.b64encode(struct.pack("<3f", *vector)).decode("ascii") if encoding_format == "base64" else vector
    item = {"object": "embedding", "embedding": embedding}
    response_data = [item] if data_is_list else item
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"data": response_data})

    monkeypatch.setenv("MEMU_CONFIG_ENV", str(tmp_path / "unused.env"))
    monkeypatch.setenv("MEMU_HTTP_PROXY", "")
    monkeypatch.setattr(httpx, "AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))
    client = HTTPEmbeddingClient(
        base_url="http://localhost",
        api_key="fixture-key",
        embed_model="doubao-embedding-vision-250615",
        provider="doubao",
    )
    vectors = await client.embed_multimodal(
        [("text", "A cat"), ("image_url", "https://example.org/cat.png")], encoding_format=encoding_format
    )

    assert vectors == [vector]
    assert len(requests) == 1
    assert requests[0].url.path == "/api/v3/embeddings/multimodal"
    assert requests[0].headers["authorization"] == "Bearer fixture-key"
    assert json.loads(requests[0].content) == {
        "model": "doubao-embedding-vision-250615",
        "encoding_format": encoding_format,
        "input": [
            {"type": "text", "text": "A cat"},
            {"type": "image_url", "image_url": {"url": "https://example.org/cat.png"}},
        ],
    }


async def test_text_embedding_response_is_unchanged(monkeypatch, tmp_path):
    def respond(request):
        assert request.url.path == "/api/v3/embeddings"
        return httpx.Response(200, json={"data": [{"embedding": [0.25, -0.5]}]})

    monkeypatch.setenv("MEMU_CONFIG_ENV", str(tmp_path / "unused.env"))
    monkeypatch.setenv("MEMU_HTTP_PROXY", "")
    monkeypatch.setattr(httpx, "AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))
    client = HTTPEmbeddingClient(
        base_url="http://localhost", api_key="fixture-key", embed_model="doubao", provider="doubao"
    )
    vectors, _ = await client.embed(["hello"])
    assert vectors == [[0.25, -0.5]]
