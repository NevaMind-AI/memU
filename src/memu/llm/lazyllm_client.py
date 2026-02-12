import asyncio
import functools
from typing import Any, cast

import lazyllm
from lazyllm import LOG


class LazyLLMClient:
    """LAZYLLM client that relies on the LazyLLM framework."""

    DEFAULT_SOURCE = "qwen"

    def __init__(
        self,
        *,
        llm_source: str | None = None,
        vlm_source: str | None = None,
        embed_source: str | None = None,
        stt_source: str | None = None,
        chat_model: str | None = None,
        vlm_model: str | None = None,
        embed_model: str | None = None,
        stt_model: str | None = None,
    ):
        self.llm_source = llm_source or self.DEFAULT_SOURCE
        self.vlm_source = vlm_source or self.DEFAULT_SOURCE
        self.embed_source = embed_source or self.DEFAULT_SOURCE
        self.stt_source = stt_source or self.DEFAULT_SOURCE
        self.chat_model = chat_model
        self.vlm_model = vlm_model
        self.embed_model = embed_model
        self.stt_model = stt_model

    async def _call_async(self, client: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Asynchronously call a LazyLLM client with given arguments and keyword arguments.
        """
        if kwargs:
            return await asyncio.to_thread(functools.partial(client, *args, **kwargs))
        else:
            return await asyncio.to_thread(client, *args)

    async def chat(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Generate a summary or response for the input text using the configured LLM backend.

        Args:
            text: The input text to summarize or process.
            max_tokens: (Optional) Maximum number of tokens to generate.
            system_prompt: (Optional) System instruction to guide the LLM behavior.
        Return:
            The generated summary text as a string.
        """
        client = lazyllm.namespace("MEMU").OnlineModule(source=self.llm_source, model=self.chat_model, type="llm")
        prompt = f"{system_prompt}\n\n" if system_prompt else ""
        full_prompt = f"{prompt}text:\n{text}"
        LOG.debug(f"Summarizing text with {self.llm_source}/{self.chat_model}")
        response = await self._call_async(client, full_prompt)
        return cast(str, response)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Generate a summary or response for the input text using the configured LLM backend.

        Args:
            text: The input text to summarize or process.
            max_tokens: (Optional) Maximum number of tokens to generate.
            system_prompt: (Optional) System instruction to guide the LLM behavior.
        Return:
            The generated summary text as a string.
        """
        client = lazyllm.namespace("MEMU").OnlineModule(source=self.llm_source, model=self.chat_model, type="llm")
        prompt = system_prompt or "Summarize the text in one short paragraph."
        full_prompt = f"{prompt}\n\ntext:\n{text}"
        LOG.debug(f"Summarizing text with {self.llm_source}/{self.chat_model}")
        response = await self._call_async(client, full_prompt)
        return cast(str, response)

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, Any]:
        """
        Process an image with a text prompt using the configured VLM (Vision-Language Model).


        Args:
            prompt: Text prompt describing the request or question about the image.
            image_path: Path to the image file to be analyzed.
            max_tokens: (Optional) Maximum number of tokens to generate.
            system_prompt: (Optional) System instruction to guide the VLM behavior.
        Return:
            A tuple containing the generated text response and None (reserved for metadata).
        """
        client = lazyllm.namespace("MEMU").OnlineModule(source=self.vlm_source, model=self.vlm_model, type="vlm")
        LOG.debug(f"Processing image with {self.vlm_source}/{self.vlm_model}: {image_path}")
        # LazyLLM VLM accepts prompt as first positional argument and image_path as keyword argument
        response = await self._call_async(client, prompt, lazyllm_files=image_path)
        return response, None

    async def embed(
        self,
        texts: list[str],
        batch_size: int = 10,
    ) -> list[list[float]]:
        """
        Generate vector embeddings for a list of text strings.

        Args:
            texts: List of text strings to embed.
            batch_size: (Optional) Batch size for processing embeddings (default: 10).
        Return:
            A list of embedding vectors (list of floats), one for each input text.
        """
        client = lazyllm.namespace("MEMU").OnlineModule(
            source=self.embed_source, model=self.embed_model, type="embed", batch_size=batch_size
        )
        LOG.debug(f"embed {len(texts)} texts with {self.embed_source}/{self.embed_model}")
        response = await self._call_async(client, texts)
        return cast(list[list[float]], response)

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        prompt: str | None = None,
    ) -> str:
        """
        Transcribe audio content to text using the configured STT (Speech-to-Text) backend.

        Args:
            audio_path: Path to the audio file to transcribe.
            language: (Optional) Language code of the audio content.
            prompt: (Optional) Text prompt to guide the transcription or translation.
        Return:
            The transcribed text as a string.
        """
        client = lazyllm.namespace("MEMU").OnlineModule(source=self.stt_source, model=self.stt_model, type="stt")
        LOG.debug(f"Transcribing audio with {self.stt_source}/{self.stt_model}: {audio_path}")
        response = await self._call_async(client, audio_path)
        return cast(str, response)
