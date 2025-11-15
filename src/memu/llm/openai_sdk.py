import logging
from typing import cast

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAISDKClient:
    """OpenAI client that relies on the official Python SDK."""

    def __init__(self, *, base_url: str, api_key: str, chat_model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> str:
        prompt = system_prompt or "Summarize the text in one short paragraph."

        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=1,
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        logger.debug("OpenAI summarize response: %s", response)
        return content or ""

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.embed_model, input=inputs)
        return [cast(list[float], d.embedding) for d in response.data]
