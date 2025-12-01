from __future__ import annotations

from typing import Any, Literal, cast

from memu.embedding.backends.base import EmbeddingBackend


class DoubaoMultimodalEmbeddingInput:
    """Represents a single input item for multimodal embedding."""

    def __init__(
        self,
        input_type: Literal["text", "image_url", "video_url"],
        content: str,
    ):
        self.input_type = input_type
        self.content = content

    def to_dict(self) -> dict[str, Any]:
        if self.input_type == "text":
            return {"type": "text", "text": self.content}
        elif self.input_type == "image_url":
            return {"type": "image_url", "image_url": {"url": self.content}}
        elif self.input_type == "video_url":
            return {"type": "video_url", "video_url": {"url": self.content}}
        else:
            msg = f"Unsupported input type: {self.input_type}"
            raise ValueError(msg)


class DoubaoEmbeddingBackend(EmbeddingBackend):
    """Backend for Doubao embedding API (including multimodal embedding)."""

    name = "doubao"
    embedding_endpoint = "/api/v3/embeddings"
    multimodal_embedding_endpoint = "/api/v3/embeddings/multimodal"

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        """Build payload for standard text embeddings."""
        return {"model": embed_model, "input": inputs, "encoding_format": "float"}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        """Parse embedding response."""
        return [cast(list[float], d["embedding"]) for d in data["data"]]

    def build_multimodal_embedding_payload(
        self,
        *,
        inputs: list[DoubaoMultimodalEmbeddingInput],
        embed_model: str,
        encoding_format: str = "float",
    ) -> dict[str, Any]:
        """
        Build payload for multimodal embedding API.

        Args:
            inputs: List of multimodal inputs (text, image_url, video_url)
            embed_model: Model name (e.g., 'doubao-embedding-vision-250615')
            encoding_format: Encoding format ('float' or 'base64')

        Returns:
            Request payload dict
        """
        return {
            "model": embed_model,
            "encoding_format": encoding_format,
            "input": [inp.to_dict() for inp in inputs],
        }

    def parse_multimodal_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        """Parse multimodal embedding response."""
        return [cast(list[float], d["embedding"]) for d in data["data"]]
