from typing import Any
import logging
from pathlib import Path
import asyncio
import lazyllm
import functools
from lazyllm import LOG

class LazyLLMClient:
    DEFAULT_SOURCE = 'qwen'

    def __init__(self,
                  *,
                llm_source: str = None,
                vlm_source: str = None,
                embed_source: str = None,
                stt_source: str = None,
                chat_model: str = None,
                vlm_model: str = None,
                embed_model: str = None,
                stt_model: str = None,
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
        '''异步调用 lazyllm client'''
        if kwargs:
            return await asyncio.to_thread(functools.partial(client, *args, **kwargs))
        else:
            return await asyncio.to_thread(client, *args)


    async def summarize(
                        self,
                        text: str,
                        *,
                        max_tokens: int | None = None,
                        system_prompt: str | None = None,
                    ) -> str:
        client = lazyllm.namespace('MEMU').OnlineModule(source=self.llm_source, model=self.chat_model, type='llm')
        prompt = system_prompt or 'Summarize the text in one short paragraph.'
        full_prompt = f'{prompt}\n\ntext:\n{text}'
        LOG.debug(f'Summarizing text with {self.llm_source}/{self.chat_model}')
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
        client = lazyllm.namespace('MEMU').OnlineModule(source=self.vlm_source, model=self.vlm_model, type='vlm')
        LOG.debug(f'Processing image with {self.vlm_source}/{self.vlm_model}: {image_path}')
        # LazyLLM VLM accepts prompt as first positional argument and image_path as keyword argument
        response = await self._call_async(client, prompt, lazyllm_files=image_path)
        return response, None

    async def embed(
                    self,
                    texts: list[str],
                    batch_size: int = 10, # optional
                ) -> list[list[float]]:
        client = lazyllm.namespace('MEMU').OnlineModule(source=self.embed_source, model=self.embed_model, 
                                                        type='embed', batch_size=batch_size)
        LOG.debug(f'embed {len(texts)} texts with {self.embed_source}/{self.embed_model}')
        response = await self._call_async(client, texts)
        return response

    async def transcribe(
                        self,
                        audio_path: str,
                        language: str | None = None,
                        prompt: str | None = None,
                    ) -> str:
        client = lazyllm.namespace('MEMU').OnlineModule(source=self.stt_source, model=self.stt_model, type='stt')
        LOG.debug(f'Transcribing audio with {self.stt_source}/{self.stt_model}: {audio_path}')
        response = await self._call_async(client, audio_path)
        return response
    