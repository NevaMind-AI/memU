"""
OpenAI LLM客户端实现
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseLLMClient, LLMResponse


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端实现"""

    def __init__(
        self, api_key: str = None, base_url: str = None, model: str = "gpt-3.5-turbo", **kwargs
    ):
        """
        初始化OpenAI客户端

        Args:
            api_key: OpenAI API密钥，如果为None则从环境变量获取
            base_url: API基础URL，支持自定义端点
            model: 默认模型
            **kwargs: 其他配置参数
        """
        super().__init__(model=model, **kwargs)

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        # 延迟导入OpenAI库
        self._client = None

    @property
    def client(self):
        """懒加载OpenAI客户端"""
        if self._client is None:
            try:
                import openai

                self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError(
                    "OpenAI library is required. Install with: pip install openai>=1.0.0"
                )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        """OpenAI chat completion"""
        model = self.get_model(model)

        try:
            # Preprocess messages
            processed_messages = self._prepare_messages(messages)

            # Filter out parameters that should not be passed to OpenAI API
            api_params = self._filter_api_params(kwargs)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=processed_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **api_params,
            )

            # Build response
            return LLMResponse(
                content=response.choices[0].message.content,
                usage=response.usage.model_dump() if response.usage else {},
                model=response.model,
                success=True,
            )

        except Exception as e:
            logging.error(f"OpenAI API call failed: {e}")
            return self._handle_error(e, model)

    def _filter_api_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """过滤掉不应该传递给OpenAI API的参数"""
        # 不应该传递给OpenAI API的参数列表
        excluded_params = {"api_key", "base_url", "provider_type", "timeout", "retry_count"}

        # 只保留OpenAI API支持的参数
        filtered = {}
        for key, value in params.items():
            if key not in excluded_params:
                filtered[key] = value

        return filtered

    def _get_default_model(self) -> str:
        """获取OpenAI默认模型"""
        return "gpt-3.5-turbo"

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """预处理OpenAI消息格式"""
        # 确保消息格式正确
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                processed.append({"role": msg["role"], "content": str(msg["content"])})
            else:
                logging.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "OpenAIClient":
        """从环境变量创建OpenAI客户端"""
        return cls()

    def __str__(self) -> str:
        return f"OpenAIClient(model={self.default_model}, base_url={self.base_url})"
