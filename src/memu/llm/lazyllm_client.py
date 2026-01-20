from typing import Any
import logging
from pathlib import Path
import asyncio
import lazyllm
from lazyllm import LOG

class LazyLLMClient:
    DEFAULT_SOURCE = 'qwen'
    DEFAULT_MODELS = {
            'llm': 'qwen-plus',
            'vlm': 'qwen-vl-plus',
            'embed': 'text-embedding-v3',
            'stt': 'qwen-audio-turbo',
    }

    def __init__(self,
                  *,
                source: str = None,
                chat_model: str = None,
                vlm_model: str = None,
                embed_model: str = None,
                stt_model: str = None,
                api_key: str = None
            ):
        self.source = source or self.DEFAULT_SOURCE
        self.chat_model = chat_model or self.DEFAULT_MODELS['llm']
        self.vlm_model = vlm_model or self.DEFAULT_MODELS['vlm']
        self.embed_model = embed_model or self.DEFAULT_MODELS['embed']
        self.stt_model = stt_model or self.DEFAULT_MODELS['stt']
        self.api_key = api_key

    async def _call_async(self, client: Any, *args: Any, **kwargs: Any) -> Any:
        '''异步调用 lazyllm client'''
        if kwargs:
            return await asyncio.to_thread(lambda: client(*args, **kwargs))
        else:
            return await asyncio.to_thread(lambda: client(*args))


    async def summarize(
                        self,
                        text: str,
                        *,
                        max_tokens: int | None = None,
                        system_prompt: str | None = None,
                    ) -> str:
        client = lazyllm.OnlineModule(source=self.source, model=self.chat_model, type='llm')
        prompt = system_prompt or 'Summarize the text in one short paragraph.'
        full_prompt = f'{prompt}\n\ntext:\n{text}'
        LOG.debug(f'Summarizing text with {self.source}/{self.chat_model}')
        response = await self._call_async(client, full_prompt)
        return response
            
    async def vision(
                    self,
                    prompt: str,
                    image_path: str,
                    *,
                    max_tokens: int | None = None,
                    system_prompt: str | None = None,
                ) -> tuple[str, Any]:
        client = lazyllm.OnlineModule(source=self.source, model=self.vlm_model, type='vlm')
        # Combine system_prompt and prompt if system_prompt exists
        full_prompt = prompt
        if system_prompt:
            full_prompt = f'{system_prompt}\n\n{prompt}'
        LOG.debug(f'Processing image with {self.source}/{self.vlm_model}: {image_path}')
        # LazyLLM VLM accepts prompt as first positional argument and image_path as keyword argument
        response = await self._call_async(client, full_prompt, image_path=image_path)
        return response, None

    async def embed(
                    self,
                    texts: list[str],
                    batch_size: int = 10, # optional
                ) -> list[list[float]]:
        client = lazyllm.OnlineModule(source=self.source, model=self.embed_model, type='embed')
        LOG.debug(f'embed {len(texts)} texts with {self.source}/{self.embed_model}')
        response = await self._call_async(client, texts)
        return response

    async def transcribe(
                        self,
                        audio_path: str,
                        language: str | None = None,
                        prompt: str | None = None,
                    ) -> str:
        client = lazyllm.OnlineModule(source=self.source, model=self.stt_model, type='stt')
        LOG.debug(f'Transcribing audio with {self.source}/{self.stt_model}: {audio_path}')
        response = await self._call_async(client, audio_path)
        return response
    