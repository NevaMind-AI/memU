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
    
    # Get the appropriate endpoint based on model name
    if not azure_endpoint:
        azure_endpoint = _get_endpoint_for_model(chat_deployment)
    
    # Check if it's a DeepSeek model
    if "deepseek" in chat_deployment.lower():
        # Ensure we have valid endpoint for DeepSeek
        # deepseek_endpoint = azure_endpoint or os.getenv("DEEPSEEK_ENDPOINT")
        deepseek_endpoint = os.getenv("DEEPSEEK_ENDPOINT")
        if not deepseek_endpoint:
            raise ValueError("DeepSeek endpoint is required")
        
        # Use DeepSeek client
        client_params = {
            "endpoint": deepseek_endpoint,
            "model_name": chat_deployment,
            "api_version": "2024-05-01-preview",  # DeepSeek uses different API version
            **kwargs
        }
        if api_key is not None:
            client_params["api_key"] = api_key
        
        return DeepSeekClient(**client_params)
    else:
        # Ensure we have valid endpoint for Azure OpenAI
        azure_openai_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        if not azure_openai_endpoint:
            raise ValueError("Azure OpenAI endpoint is required")
        
        # Use Azure OpenAI client (default)
        client_params = {
            "azure_endpoint": azure_openai_endpoint,
            "deployment_name": chat_deployment,
            "use_entra_id": use_entra_id,
            "api_version": api_version,
            **kwargs
        }
        if api_key is not None:
            client_params["api_key"] = api_key
        
        return AzureOpenAIClient(**client_params)


def _get_endpoint_for_model(chat_deployment: str) -> Optional[str]:
    """
    Get the appropriate endpoint based on the specific model name
    
    Args:
        chat_deployment: Model/deployment name
        
    Returns:
        str: Appropriate endpoint URL
    """
    # Model-specific endpoint routing
    if chat_deployment == "gpt-4.1-mini-2":
        return os.getenv("AZURE_OPENAI_ENDPOINT_1")
    elif chat_deployment == "DeepSeek-V3-0324":
        return os.getenv("DEEPSEEK_ENDPOINT_2")
    elif "deepseek" in chat_deployment.lower():
        # Fallback for other DeepSeek models
        return os.getenv("DEEPSEEK_ENDPOINT") or os.getenv("DEEPSEEK_ENDPOINT_2")
    else:
        # Fallback for other Azure OpenAI models
        return os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT_1")


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