import logging
from typing import cast

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbeddingSDKClient:
    """OpenAI embedding client that relies on the official Python SDK."""

    def __init__(self, *, base_url: str, api_key: str, embed_model: str, batch_size: int = 25):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.embed_model = embed_model
        self.batch_size = batch_size
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        """
        Create text embeddings.

        Args:
            inputs: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        # Process in batches to handle API limits (e.g., some providers limit batch size)
        if len(inputs) <= self.batch_size:
            # Single batch - direct call
            response = await self.client.embeddings.create(model=self.embed_model, input=inputs)
            return [cast(list[float], d.embedding) for d in response.data]

        # Multiple batches - split and merge
        all_embeddings = []
        for i in range(0, len(inputs), self.batch_size):
            batch = inputs[i : i + self.batch_size]
            response = await self.client.embeddings.create(model=self.embed_model, input=batch)
            batch_embeddings = [cast(list[float], d.embedding) for d in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings
