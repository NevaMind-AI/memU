from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from memu.vlm.base import VLMClient, encode_image

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletion,
        ChatCompletionContentPartImageParam,
        ChatCompletionContentPartTextParam,
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
    )

logger = logging.getLogger(__name__)


class OpenAIVLMClient(VLMClient):
    """Vision-language client backed by the official OpenAI Python SDK."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        vlm_model: str,
    ):
        from openai import AsyncOpenAI

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.vlm_model = vlm_model
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, ChatCompletion]:
        from openai import omit

        base64_image, mime_type = encode_image(image_path)

        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            system_message: ChatCompletionSystemMessageParam = {"role": "system", "content": system_prompt}
            messages.append(system_message)

        text_part: ChatCompletionContentPartTextParam = {"type": "text", "text": prompt}
        image_part: ChatCompletionContentPartImageParam = {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
        }
        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": [text_part, image_part],
        }
        messages.append(user_message)

        response = await self.client.chat.completions.create(
            model=self.vlm_model,
            messages=messages,
            temperature=1,
            # GPT-5 models reject ``max_tokens`` (and ``max_tokens=None``); omit when
            # unset, otherwise use ``max_completion_tokens`` (works for GPT-4o too).
            max_completion_tokens=max_tokens if max_tokens is not None else omit,
        )
        content = response.choices[0].message.content
        logger.debug("OpenAI VLM vision response: %s", response)
        return content or "", response
