"""Tests for GeminiEmbeddingBackend multimodal support."""
from __future__ import annotations

import base64

import pytest

from memu.embedding.backends.gemini import GeminiEmbeddingBackend

MODEL = "text-embedding-004"


@pytest.fixture
def backend():
    return GeminiEmbeddingBackend()


class TestBuildEmbeddingPayloadTextOnly:
    """Backward-compatible text-only inputs."""

    def test_single_text(self, backend: GeminiEmbeddingBackend):
        payload = backend.build_embedding_payload(inputs=["hello"], embed_model=MODEL)
        assert payload == {
            "requests": [
                {
                    "model": f"models/{MODEL}",
                    "content": {"parts": [{"text": "hello"}]},
                }
            ]
        }

    def test_multiple_texts(self, backend: GeminiEmbeddingBackend):
        payload = backend.build_embedding_payload(inputs=["a", "b"], embed_model=MODEL)
        assert len(payload["requests"]) == 2
        assert payload["requests"][0]["content"]["parts"] == [{"text": "a"}]
        assert payload["requests"][1]["content"]["parts"] == [{"text": "b"}]


class TestBuildEmbeddingPayloadImageOnly:
    """Dict inputs with image only."""

    def test_image_bytes(self, backend: GeminiEmbeddingBackend):
        raw = b"\x89PNG"
        payload = backend.build_embedding_payload(
            inputs=[{"image": raw, "mime_type": "image/png"}],
            embed_model=MODEL,
        )
        parts = payload["requests"][0]["content"]["parts"]
        assert len(parts) == 1
        assert parts[0] == {
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(raw).decode(),
            }
        }

    def test_image_already_base64(self, backend: GeminiEmbeddingBackend):
        b64 = "iVBORw0KGgo="
        payload = backend.build_embedding_payload(
            inputs=[{"image": b64, "mime_type": "image/png"}],
            embed_model=MODEL,
        )
        parts = payload["requests"][0]["content"]["parts"]
        assert parts[0]["inline_data"]["data"] == b64

    def test_default_mime_type(self, backend: GeminiEmbeddingBackend):
        payload = backend.build_embedding_payload(
            inputs=[{"image": b"\x00"}],
            embed_model=MODEL,
        )
        assert payload["requests"][0]["content"]["parts"][0]["inline_data"]["mime_type"] == "image/png"


class TestBuildEmbeddingPayloadMultimodal:
    """Dict inputs with both text and image."""

    def test_text_and_image(self, backend: GeminiEmbeddingBackend):
        raw = b"\xff\xd8"
        payload = backend.build_embedding_payload(
            inputs=[{"text": "a cat", "image": raw, "mime_type": "image/jpeg"}],
            embed_model=MODEL,
        )
        parts = payload["requests"][0]["content"]["parts"]
        assert len(parts) == 2
        assert parts[0] == {"text": "a cat"}
        assert parts[1] == {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(raw).decode(),
            }
        }


class TestBuildEmbeddingPayloadMixed:
    """Mix of str and dict inputs in a single call."""

    def test_mixed_inputs(self, backend: GeminiEmbeddingBackend):
        payload = backend.build_embedding_payload(
            inputs=["plain text", {"image": b"\x00", "mime_type": "image/png"}],
            embed_model=MODEL,
        )
        assert len(payload["requests"]) == 2
        assert payload["requests"][0]["content"]["parts"] == [{"text": "plain text"}]
        assert "inline_data" in payload["requests"][1]["content"]["parts"][0]


class TestParseEmbeddingResponse:
    def test_parse(self, backend: GeminiEmbeddingBackend):
        data = {"embeddings": [{"values": [0.1, 0.2]}, {"values": [0.3, 0.4]}]}
        assert backend.parse_embedding_response(data) == [[0.1, 0.2], [0.3, 0.4]]

    def test_parse_empty(self, backend: GeminiEmbeddingBackend):
        assert backend.parse_embedding_response({}) == []
