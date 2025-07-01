"""
LLM基础抽象类和数据结构
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM响应结果"""
    content: str
    usage: Dict[str, int]
    model: str
    success: bool
    error: Optional[str] = None
    
    def __bool__(self) -> bool:
        """使响应对象可以作为布尔值使用"""
        return self.success
    
    def __str__(self) -> str:
        """字符串表示返回内容"""
        return self.content


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, model: str = None, **kwargs):
        """
        初始化LLM客户端
        
        Args:
            model: 默认模型名称
            **kwargs: 其他配置参数
        """
        self.default_model = model
        self.config = kwargs
        
    @abstractmethod
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """
        聊天补全接口
        
        Args:
            messages: 对话消息列表
            model: 模型名称，如果为None则使用default_model
            temperature: 生成温度
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 响应结果
        """
        pass
    
    def simple_chat(self, prompt: str, **kwargs) -> str:
        """
        简单聊天接口，返回字符串内容
        
        Args:
            prompt: 用户输入
            **kwargs: 其他参数
            
        Returns:
            str: AI回复内容
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.chat_completion(messages, **kwargs)
        return response.content if response.success else f"Error: {response.error}"
    
    def get_model(self, model: str = None) -> str:
        """获取要使用的模型名称"""
        return model or self.default_model or self._get_default_model()
    
    @abstractmethod
    def _get_default_model(self) -> str:
        """获取提供商的默认模型"""
        pass
    
    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """预处理消息格式，子类可以重写"""
        return messages
    
    def _handle_error(self, error: Exception, model: str) -> LLMResponse:
        """统一的错误处理"""
        return LLMResponse(
            content="",
            usage={},
            model=model,
            success=False,
            error=str(error)
        ) 