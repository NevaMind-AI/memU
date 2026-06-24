import logging
from typing import cast

from openai import AsyncOpenAI
from openai.types import CreateEmbeddingResponse

logger = logging.getLogger(__name__)


class OpenAIEmbeddingSDKClient:
    """OpenAI embedding client that relies on the official Python SDK."""

    def __init__(self, *, base_url: str, api_key: str, embed_model: str, batch_size: int = 1):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.embed_model = embed_model
        self.batch_size = batch_size
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], CreateEmbeddingResponse | None]:
        """
        Create text embeddings via the official SDK.

        Args:
            inputs: List of text strings to embed

        Returns:
            Tuple of (list of embedding vectors, last raw response). The raw
            response carries token ``usage`` so callers/interceptors can track
            consumption. For batched requests only the last response is returned.
        """
        # Process in batches to handle API limits (e.g., some providers limit batch size)
        if len(inputs) <= self.batch_size:
            # Single batch - direct call
            response = await self.client.embeddings.create(model=self.embed_model, input=inputs)
            return [cast(list[float], d.embedding) for d in response.data], response

        # Multiple batches - split and merge
        all_embeddings: list[list[float]] = []
        last_response: CreateEmbeddingResponse | None = None
        for i in range(0, len(inputs), self.batch_size):
            batch = inputs[i : i + self.batch_size]
            response = await self.client.embeddings.create(model=self.embed_model, input=batch)
            all_embeddings.extend([cast(list[float], d.embedding) for d in response.data])
            last_response = response

        return all_embeddings, last_response
