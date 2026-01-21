from typing import Any
import logging
from pathlib import Path
import asyncio
import lazyllm
from lazyllm import LOG

class LazyLLMClient:
    DEFAULT_SOURCE = 'qwen'
    DEFAULT_MODELS = {
            'llm': 'qwen3-max',
            'vlm': 'qwen-vl-plus',
            'embed': 'text-embedding-v3',
            'stt': 'qwen-audio-turbo',
    }

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
                api_key: str = None,
            ):
        self.llm_source = llm_source or self.source
        self.vlm_source = vlm_source or self.source
        self.embed_source = embed_source or self.source
        self.stt_source = stt_source or self.source
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
        client = lazyllm.OnlineModule(source=self.llm_source, model=self.chat_model, type='llm', api_key=self.api_key)
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
        client = lazyllm.OnlineModule(source=self.vlm_source, model=self.vlm_model, type='vlm', api_key=self.api_key)
        LOG.debug(f'Processing image with {self.vlm_source}/{self.vlm_model}: {image_path}')
        # LazyLLM VLM accepts prompt as first positional argument and image_path as keyword argument
        response = await self._call_async(client, prompt, image_path=image_path)
        return response, None

    async def embed(
                    self,
                    texts: list[str],
                    batch_size: int = 10, # optional
                ) -> list[list[float]]:
        client = lazyllm.OnlineModule(source=self.embed_source, model=self.embed_model, type='embed', 
                                        batch_size=batch_size, api_key=self.api_key)
        LOG.debug(f'embed {len(texts)} texts with {self.embed_source}/{self.embed_model}')
        response = await self._call_async(client, texts)
        return response

    async def transcribe(
                        self,
                        audio_path: str,
                        language: str | None = None,
                        prompt: str | None = None,
                    ) -> str:
        client = lazyllm.OnlineModule(source=self.stt_source, model=self.stt_model, type='stt', api_key=self.api_key)
        LOG.debug(f'Transcribing audio with {self.stt_source}/{self.stt_model}: {audio_path}')
        response = await self._call_async(client, audio_path)
        return response
    