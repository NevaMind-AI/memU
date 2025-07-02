"""
Anthropic (Claude) LLM客户端实现
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseLLMClient, LLMResponse


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude客户端实现"""

    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229", **kwargs):
        """
        初始化Anthropic客户端

        Args:
            api_key: Anthropic API密钥，如果为None则从环境变量获取
            model: 默认模型
            **kwargs: 其他配置参数
        """
        super().__init__(model=model, **kwargs)

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        # 延迟导入Anthropic库
        self._client = None

    @property
    def client(self):
        """懒加载Anthropic客户端"""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic library is required. Install with: pip install anthropic>=0.7.0"
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
        """Anthropic聊天补全"""
        model = self.get_model(model)

        try:
            # 预处理消息
            processed_messages = self._prepare_messages(messages)

            # 调用Anthropic API
            response = self.client.messages.create(
                model=model,
                messages=processed_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # 构造响应
            content = ""
            if response.content:
                # Claude返回的content是一个列表
                content = "".join(
                    [block.text for block in response.content if hasattr(block, "text")]
                )

            usage = {
                "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                "completion_tokens": getattr(response.usage, "output_tokens", 0),
                "total_tokens": getattr(response.usage, "input_tokens", 0)
                + getattr(response.usage, "output_tokens", 0),
            }

            return LLMResponse(content=content, usage=usage, model=response.model, success=True)

        except Exception as e:
            logging.error(f"Anthropic API调用失败: {e}")
            return self._handle_error(e, model)

    def _get_default_model(self) -> str:
        """获取Anthropic默认模型"""
        return "claude-3-sonnet-20240229"

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """预处理Anthropic消息格式"""
        processed = []

        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                role = msg["role"]
                content = str(msg["content"])

                # Anthropic的角色映射
                if role == "system":
                    # Claude不支持system角色，需要转换为user消息
                    processed.append({"role": "user", "content": f"System: {content}"})
                elif role in ["user", "assistant"]:
                    processed.append({"role": role, "content": content})
                else:
                    logging.warning(f"Unknown role '{role}', treating as user")
                    processed.append({"role": "user", "content": content})
            else:
                logging.warning(f"Invalid message format: {msg}")

        return processed

    @classmethod
    def from_env(cls) -> "AnthropicClient":
        """从环境变量创建Anthropic客户端"""
        return cls()

    def __str__(self) -> str:
        return f"AnthropicClient(model={self.default_model})"
