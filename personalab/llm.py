"""
LLM接口模块

提供统一的LLM接口，支持多种LLM服务（OpenAI等）
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM响应结果"""
    content: str
    usage: Dict[str, int]
    model: str
    success: bool
    error: Optional[str] = None


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """聊天补全接口"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端"""
    
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """OpenAI聊天补全"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                usage=response.usage.model_dump() if response.usage else {},
                model=response.model,
                success=True
            )
            
        except Exception as e:
            logging.error(f"OpenAI API调用失败: {e}")
            return LLMResponse(
                content="",
                usage={},
                model=model,
                success=False,
                error=str(e)
            )


class LLMClientFactory:
    """LLM客户端工厂类"""
    
    @staticmethod
    def create_client(
        client_type: str = "openai",
        api_key: str = None,
        base_url: str = None,
        **kwargs
    ) -> BaseLLMClient:
        """
        创建LLM客户端
        
        Args:
            client_type: 客户端类型 ("openai")
            api_key: API密钥
            base_url: API基础URL
            **kwargs: 其他参数
            
        Returns:
            LLM客户端实例
        """
        if client_type.lower() == "openai":
            if not api_key:
                raise ValueError("OpenAI客户端需要提供api_key")
            return OpenAIClient(api_key=api_key, base_url=base_url)
        
        else:
            raise ValueError(f"不支持的客户端类型: {client_type}")


# 便捷函数
def create_llm_client(client_type: str = "openai", **kwargs) -> BaseLLMClient:
    """创建LLM客户端的便捷函数"""
    return LLMClientFactory.create_client(client_type, **kwargs) 