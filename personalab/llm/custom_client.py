"""
自定义LLM客户端，支持用户自定义实现
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseLLMClient, LLMResponse


class CustomLLMClient(BaseLLMClient):
    """
    自定义LLM客户端，支持用户传入自定义的LLM函数或对象

    使用场景：
    1. 本地模型（如Ollama、HuggingFace Transformers等）
    2. 自定义API端点
    3. Mock/测试用途
    4. 其他第三方LLM服务
    """

    def __init__(
        self,
        llm_function: Union[Callable, object] = None,
        model: str = "custom-model",
        function_type: str = "simple",
        **kwargs,
    ):
        """
        初始化自定义LLM客户端

        Args:
            llm_function: 自定义LLM函数或对象
                - 如果是函数，应该接受(messages, **kwargs)并返回字符串或LLMResponse
                - 如果是对象，应该有chat_completion方法
            model: 模型名称
            function_type: 函数类型
                - "simple": 函数返回字符串
                - "full": 函数返回LLMResponse对象
                - "object": 对象，有chat_completion方法
            **kwargs: 其他配置参数
        """
        super().__init__(model=model, **kwargs)

        if llm_function is None:
            raise ValueError("llm_function is required for CustomLLMClient")

        self.llm_function = llm_function
        self.function_type = function_type

        # 验证函数类型
        if function_type == "object":
            if not hasattr(llm_function, "chat_completion"):
                raise ValueError("Object must have 'chat_completion' method")
        elif function_type not in ["simple", "full"]:
            raise ValueError("function_type must be 'simple', 'full', or 'object'")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        """自定义LLM聊天补全"""
        model = self.get_model(model)

        try:
            # 准备参数
            call_kwargs = {"temperature": temperature, "max_tokens": max_tokens, **kwargs}

            if self.function_type == "object":
                # 调用对象的chat_completion方法
                result = self.llm_function.chat_completion(
                    messages=messages, model=model, **call_kwargs
                )

                # 如果返回的是LLMResponse，直接返回；否则包装
                if isinstance(result, LLMResponse):
                    return result
                else:
                    return LLMResponse(content=str(result), usage={}, model=model, success=True)

            elif self.function_type == "full":
                # 函数返回LLMResponse
                result = self.llm_function(messages, **call_kwargs)
                if isinstance(result, LLMResponse):
                    return result
                else:
                    logging.warning("Function declared as 'full' but didn't return LLMResponse")
                    return LLMResponse(content=str(result), usage={}, model=model, success=True)

            else:  # function_type == "simple"
                # 函数返回字符串
                result = self.llm_function(messages, **call_kwargs)
                return LLMResponse(content=str(result), usage={}, model=model, success=True)

        except Exception as e:
            logging.error(f"Custom LLM function failed: {e}")
            return self._handle_error(e, model)

    def _get_default_model(self) -> str:
        """获取自定义模型默认名称"""
        return "custom-model"

    @classmethod
    def create_full(cls, llm_function: Callable) -> "CustomLLMClient":
        """
        创建完整的自定义客户端（函数返回LLMResponse）

        Args:
            llm_function: 接受(messages, **kwargs)，返回LLMResponse的函数

        Returns:
            CustomLLMClient实例
        """
        return cls(llm_function=llm_function, function_type="full")

    @classmethod
    def create_object(cls, llm_object: object) -> "CustomLLMClient":
        """
        创建基于对象的自定义客户端

        Args:
            llm_object: 有chat_completion方法的对象

        Returns:
            CustomLLMClient实例
        """
        return cls(llm_function=llm_object, function_type="object")

    def __str__(self) -> str:
        return f"CustomLLMClient(type={self.function_type}, model={self.default_model})"


def create_simple_client(llm_function: Callable) -> CustomLLMClient:
    """创建简单客户端的便捷函数"""
    return CustomLLMClient.create_simple(llm_function)
