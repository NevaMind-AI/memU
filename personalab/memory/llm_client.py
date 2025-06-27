"""
LLM接口模块

提供统一的LLM接口，支持多种LLM服务（OpenAI, Claude, 本地模型等）
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


class MockLLMClient(BaseLLMClient):
    """模拟LLM客户端，用于测试和演示"""
    
    def __init__(self):
        self.model_name = "mock-llm"
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "mock-llm",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """模拟LLM响应"""
        
        # 获取最后一条用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        # 根据不同的prompt类型生成不同的响应
        if "分析对话并提取" in user_message:
            # Memory分析响应
            response_content = self._generate_memory_analysis_response(messages)
        elif "更新用户画像" in user_message:
            # 画像更新响应
            response_content = self._generate_profile_update_response(messages)
        elif "Theory of Mind" in user_message:
            # ToM分析响应
            response_content = self._generate_tom_analysis_response(messages)
        else:
            # 通用响应
            response_content = self._generate_generic_response(user_message)
        
        return LLMResponse(
            content=response_content,
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            model=self.model_name,
            success=True
        )
    
    def _generate_memory_analysis_response(self, messages: List[Dict[str, str]]) -> str:
        """生成Memory分析响应"""
        return json.dumps({
            "profile_updates": [
                "用户是一名软件工程师，擅长Python编程",
                "用户对机器学习和深度学习有浓厚兴趣"
            ],
            "events": [
                "用户介绍了自己的职业背景",
                "用户表达了对技术学习的热情"
            ],
            "confidence": 0.85
        }, ensure_ascii=False)
    
    def _generate_profile_update_response(self, messages: List[Dict[str, str]]) -> str:
        """生成画像更新响应"""
        return "用户是一名25岁的软件工程师，来自北京，主要从事数据分析和AI模型开发工作。对Python和机器学习技术有深入了解，目前正在学习PyTorch深度学习框架。"
    
    def _generate_tom_analysis_response(self, messages: List[Dict[str, str]]) -> str:
        """生成ToM分析响应"""
        return json.dumps({
            "intent_analysis": {
                "primary_intent": "information_sharing",
                "confidence": 0.8
            },
            "emotion_analysis": {
                "dominant_emotion": "enthusiastic",
                "confidence": 0.7
            },
            "behavior_patterns": {
                "communication_style": "direct_and_informative",
                "engagement_level": "high"
            },
            "cognitive_state": {
                "knowledge_level": "advanced",
                "learning_orientation": "growth_minded"
            }
        }, ensure_ascii=False)
    
    def _generate_generic_response(self, user_message: str) -> str:
        """生成通用响应"""
        return f"收到消息：{user_message[:50]}..."


class LLMClientFactory:
    """LLM客户端工厂类"""
    
    @staticmethod
    def create_client(
        client_type: str = "mock",
        api_key: str = None,
        base_url: str = None,
        **kwargs
    ) -> BaseLLMClient:
        """
        创建LLM客户端
        
        Args:
            client_type: 客户端类型 ("openai", "mock")
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
        
        elif client_type.lower() == "mock":
            return MockLLMClient()
        
        else:
            raise ValueError(f"不支持的客户端类型: {client_type}")


# 便捷函数
def create_llm_client(client_type: str = "mock", **kwargs) -> BaseLLMClient:
    """创建LLM客户端的便捷函数"""
    return LLMClientFactory.create_client(client_type, **kwargs) 