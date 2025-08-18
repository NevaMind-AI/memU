"""
Custom LLM client supporting user-defined implementations
"""

from typing import Callable, Dict, List, Union

from .base import BaseLLMClient, LLMResponse
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CustomLLMClient(BaseLLMClient):
    """
    Custom LLM client supporting user-provided custom LLM functions or objects

    Use cases:
    1. Local models (such as Ollama, HuggingFace Transformers, etc.)
    2. Custom API endpoints
    3. Mock/testing purposes
    4. Other third-party LLM services
    """

    def __init__(
        self,
        llm_function: Union[Callable, object] = None,
        model: str = "custom-model",
        function_type: str = "simple",
        **kwargs,
    ):
        """
        Initialize custom LLM client

        Args:
            llm_function: Custom LLM function or object
                - If function, should accept (messages, **kwargs) and return string or LLMResponse
                - If object, should have chat_completion method
            model: Model name
            function_type: Function type
                - "simple": Function returns string
                - "full": Function returns LLMResponse object
                - "object": Object with chat_completion method
            **kwargs: Other configuration parameters
        """
        super().__init__(model=model, **kwargs)

        if llm_function is None:
            raise ValueError("llm_function is required for CustomLLMClient")

        self.llm_function = llm_function
        self.function_type = function_type

        # Validate function type
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
        max_tokens: int = None,
        **kwargs,
    ) -> LLMResponse:
        """Custom LLM chat completion"""
        model = self.get_model(model)
        resolved_max_tokens = self._get_max_tokens(max_tokens)

        try:
            # Prepare parameters
            call_kwargs = {
                "temperature": temperature,
                "max_tokens": resolved_max_tokens,
                **kwargs,
            }

            if self.function_type == "object":
                # Call object's chat_completion method
                result = self.llm_function.chat_completion(
                    messages=messages, model=model, **call_kwargs
                )

                # If returns LLMResponse, return directly; otherwise wrap
                if isinstance(result, LLMResponse):
                    return result
                else:
                    return LLMResponse(
                        content=str(result), usage={}, model=model, success=True
                    )

            elif self.function_type == "full":
                # Function returns LLMResponse
                result = self.llm_function(messages, **call_kwargs)
                if isinstance(result, LLMResponse):
                    return result
                else:
                    logger.warning(
                        "Function declared as 'full' but didn't return LLMResponse"
                    )
                    return LLMResponse(
                        content=str(result), usage={}, model=model, success=True
                    )

            else:  # function_type == "simple"
                # Function returns string
                result = self.llm_function(messages, **call_kwargs)
                return LLMResponse(
                    content=str(result), usage={}, model=model, success=True
                )

        except Exception as e:
            logger.error(f"Custom LLM function failed: {e}")
            return self._handle_error(e, model)

    def _get_default_model(self) -> str:
        """Get custom model default name"""
        return "custom-model"

    @classmethod
    def create_full(cls, llm_function: Callable) -> "CustomLLMClient":
        """
        Create full custom client (function returns LLMResponse)

        Args:
            llm_function: Function accepting (messages, **kwargs), returning LLMResponse

        Returns:
            CustomLLMClient instance
        """
        return cls(llm_function=llm_function, function_type="full")

    @classmethod
    def create_object(cls, llm_object: object) -> "CustomLLMClient":
        """
        Create object-based custom client

        Args:
            llm_object: Object with chat_completion method

        Returns:
            CustomLLMClient instance
        """
        return cls(llm_function=llm_object, function_type="object")

    def __str__(self) -> str:
        return f"CustomLLMClient(type={self.function_type}, model={self.default_model})"


def create_simple_client(llm_function: Callable) -> CustomLLMClient:
    """Convenience function to create simple client"""
    return CustomLLMClient.create_simple(llm_function)
