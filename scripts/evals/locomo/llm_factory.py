"""
LLM Client Factory

This module provides factory functions to create appropriate LLM clients
based on deployment/model names.
"""

import os
from typing import Optional, Union
from memu.llm import AzureOpenAIClient, DeepSeekClient, BaseLLMClient


def create_llm_client(
    chat_deployment: str,
    azure_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    use_entra_id: bool = False,
    api_version: str = "2024-02-01",
    **kwargs
) -> BaseLLMClient:
    """
    Create appropriate LLM client based on deployment name
    
    Args:
        chat_deployment: Model/deployment name
        azure_endpoint: Azure endpoint (for Azure OpenAI)
        api_key: API key
        use_entra_id: Whether to use Entra ID (for Azure OpenAI)
        api_version: API version
        **kwargs: Additional client-specific parameters
        
    Returns:
        BaseLLMClient: Appropriate LLM client instance
    """
    
    # Check if it's a DeepSeek model
    if "deepseek" in chat_deployment.lower():
        # Use DeepSeek client
        return DeepSeekClient(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            endpoint=azure_endpoint or os.getenv("DEEPSEEK_ENDPOINT"),
            model_name=chat_deployment,
            api_version="2024-05-01-preview",  # DeepSeek uses different API version
            **kwargs
        )
    else:
        # Use Azure OpenAI client (default)
        return AzureOpenAIClient(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            deployment_name=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            **kwargs
        )


def is_deepseek_model(chat_deployment: str) -> bool:
    """
    Check if the given deployment is a DeepSeek model
    
    Args:
        chat_deployment: Model/deployment name
        
    Returns:
        bool: True if it's a DeepSeek model
    """
    return "deepseek" in chat_deployment.lower()


def get_default_client_params(chat_deployment: str) -> dict:
    """
    Get default parameters for a specific client type
    
    Args:
        chat_deployment: Model/deployment name
        
    Returns:
        dict: Default parameters for the client
    """
    if is_deepseek_model(chat_deployment):
        return {
            "api_version": "2024-05-01-preview",
            "model_name": chat_deployment,
        }
    else:
        return {
            "api_version": "2024-02-01",
            "deployment_name": chat_deployment,
        } 