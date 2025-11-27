import logging
from typing import cast

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbeddingSDKClient:
    """OpenAI embedding client that relies on the official Python SDK."""

    def __init__(self, *, base_url: str, api_key: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.embed_model = embed_model
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        """
        Create text embeddings.

        Args:
            inputs: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        response = await self.client.embeddings.create(model=self.embed_model, input=inputs)
        return [cast(list[float], d.embedding) for d in response.data]
