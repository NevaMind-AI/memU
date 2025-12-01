import base64
import logging
from pathlib import Path
from typing import Any, Literal

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

logger = logging.getLogger(__name__)


class OpenAISDKClient:
    """OpenAI LLM client that relies on the official Python SDK."""

    def __init__(self, *, base_url: str, api_key: str, chat_model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> str:
        prompt = system_prompt or "Summarize the text in one short paragraph."

        system_message: ChatCompletionSystemMessageParam = {"role": "system", "content": prompt}
        user_message: ChatCompletionUserMessageParam = {"role": "user", "content": text}
        messages: list[ChatCompletionMessageParam] = [system_message, user_message]

        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=1,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        logger.debug("OpenAI summarize response: %s", response)
        return content or ""

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Call OpenAI Vision API with an image.

        Args:
            prompt: Text prompt to send with the image
            image_path: Path to the image file
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            LLM response text
        """
        # Read and encode image as base64
        image_data = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Detect image format
        suffix = Path(image_path).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(suffix, "image/jpeg")

        # Build messages with image
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            system_message: ChatCompletionSystemMessageParam = {
                "role": "system",
                "content": system_prompt,
            }
            messages.append(system_message)

        text_part: ChatCompletionContentPartTextParam = {"type": "text", "text": prompt}
        image_part: ChatCompletionContentPartImageParam = {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}",
            },
        }
        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": [text_part, image_part],
        }
        messages.append(user_message)

        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=1,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        logger.debug("OpenAI vision response: %s", response)
        return content or ""

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: Literal["text", "json", "verbose_json"] = "text",
    ) -> str:
        """
        Transcribe audio file using OpenAI Audio API.

        Args:
            audio_path: Path to the audio file
            prompt: Optional prompt to guide the transcription
            language: Optional language code (e.g., 'en', 'zh')
            response_format: Response format ('text', 'json', 'verbose_json')

        Returns:
            Transcribed text
        """
        try:
            # Use gpt-4o-mini-transcribe for better performance and cost
            kwargs: dict[str, Any] = {}
            if prompt is not None:
                kwargs["prompt"] = prompt
            if language is not None:
                kwargs["language"] = language
            with open(audio_path, "rb") as audio_stream:
                transcription = await self.client.audio.transcriptions.create(
                    file=audio_stream,
                    model="gpt-4o-mini-transcribe",
                    response_format=response_format,
                    **kwargs,
                )

            # Handle different response formats
            if response_format == "text":
                result = transcription if isinstance(transcription, str) else transcription.text
            else:
                result = transcription.text if hasattr(transcription, "text") else str(transcription)

            logger.debug("OpenAI transcribe response for %s: %s chars", audio_path, len(result))
        except Exception:
            logger.exception("Audio transcription failed for %s", audio_path)
            raise
        else:
            return result or ""
