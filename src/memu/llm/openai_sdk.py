import base64
import logging
from pathlib import Path
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
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}",
                    },
                },
            ],
        })
        
        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=1,
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        logger.debug("OpenAI vision response: %s", response)
        return content or ""

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.embed_model, input=inputs)
        return [cast(list[float], d.embedding) for d in response.data]
    
    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: str = "text",
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
            with open(audio_path, "rb") as audio_file:
                # Use gpt-4o-mini-transcribe for better performance and cost
                transcription = await self.client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file,
                    response_format=response_format,
                    prompt=prompt,
                    language=language,
                )
            
            # Handle different response formats
            if response_format == "text":
                result = transcription if isinstance(transcription, str) else transcription.text
            else:
                result = transcription.text if hasattr(transcription, "text") else str(transcription)
            
            logger.debug("OpenAI transcribe response for %s: %s chars", audio_path, len(result))
            return result or ""
            
        except Exception as e:
            logger.error("Audio transcription failed for %s: %s", audio_path, e)
            raise