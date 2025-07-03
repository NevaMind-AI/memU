"""
LLM Basic Abstract Classes and Data Structures
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class LLMResponse:
    """LLM Response Result"""

    content: str
    usage: Dict[str, int]
    model: str
    success: bool
    error: Optional[str] = None

    def __bool__(self) -> bool:
        """Enable response object to be used as boolean value"""
        return self.success

    def __str__(self) -> str:
        """String representation returns content"""
        return self.content


class BaseLLMClient(ABC):
    """LLM Client Base Class"""

    def __init__(self, model: str = None, **kwargs):
        """
        Initialize LLM Client

        Args:
            model: Default model name
            **kwargs: Other configuration parameters
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
        **kwargs,
    ) -> LLMResponse:
        """
        Chat Completion Interface

        Args:
            messages: List of conversation messages
            model: Model name, uses default_model if None
            temperature: Generation temperature
            max_tokens: Maximum number of tokens
            **kwargs: Other parameters

        Returns:
            LLMResponse: Response result
        """
        pass

    def simple_chat(self, prompt: str, **kwargs) -> str:
        """
        Simple chat interface, returns string content

        Args:
            prompt: User input
            **kwargs: Other parameters

        Returns:
            str: AI response content
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.chat_completion(messages, **kwargs)
        return response.content if response.success else f"Error: {response.error}"

    def get_model(self, model: str = None) -> str:
        """Get the model name to use"""
        return model or self.default_model or self._get_default_model()

    @abstractmethod
    def _get_default_model(self) -> str:
        """Get provider's default model"""
        pass

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Preprocess message format, can be overridden by subclasses"""
        return messages

    def _handle_error(self, error: Exception, model: str) -> LLMResponse:
        """Unified error handling"""
        return LLMResponse(
            content="", usage={}, model=model, success=False, error=str(error)
        )
