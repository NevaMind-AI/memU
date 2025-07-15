"""
Azure OpenAI Embedding Provider Implementation
"""

import logging
import os
from typing import List, Optional

from .embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Azure OpenAI embedding provider using text-embedding models.

    Supports both API key and Entra ID authentication.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2025-01-01-preview",
        deployment_name: str = "text-embedding-3-large",
        model: str = "text-embedding-3-large",
        use_entra_id: bool = False,
        **kwargs
    ):
        """
        Initialize Azure OpenAI Embedding Provider

        Args:
            api_key: Azure OpenAI API key (not needed if using Entra ID)
            azure_endpoint: Azure OpenAI endpoint URL
            api_version: Azure OpenAI API version
            deployment_name: Azure OpenAI deployment name for embedding model
            model: Embedding model name (for dimension calculation)
            use_entra_id: Whether to use Entra ID authentication
        """
        self.model = model
        self.deployment_name = deployment_name
        self.use_entra_id = use_entra_id
        
        # Set embedding dimensions based on model
        if "text-embedding-3-large" in model:
            self._dimension = 3072
        elif "text-embedding-3-small" in model:
            self._dimension = 1536
        elif "text-embedding-ada-002" in model:
            self._dimension = 1536
        else:
            self._dimension = 1536  # Default
            
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "https://openaialluci.openai.azure.com/")
        self.api_version = api_version

        if not self.use_entra_id and not self.api_key:
            raise ValueError(
                "Azure OpenAI API key is required when not using Entra ID. "
                "Set AZURE_OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        if not self.azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. "
                "Set AZURE_OPENAI_ENDPOINT environment variable or pass azure_endpoint parameter."
            )

        try:
            from openai import AzureOpenAI
            
            if self.use_entra_id:
                # Use Entra ID authentication
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default"
                )
                
                self.client = AzureOpenAI(
                    azure_endpoint=self.azure_endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=self.api_version,
                )
            else:
                # Support both API key and AzureKeyCredential authentication
                try:
                    from azure.core.credentials import AzureKeyCredential
                    
                    # Try using AzureKeyCredential first (like user's example)
                    self.client = AzureOpenAI(
                        api_version=self.api_version,
                        azure_endpoint=self.azure_endpoint,
                        azure_ad_token_provider=None,
                        api_key=self.api_key,
                    )
                except ImportError:
                    # Fallback to standard API key authentication
                    self.client = AzureOpenAI(
                        api_key=self.api_key,
                        azure_endpoint=self.azure_endpoint,
                        api_version=self.api_version,
                    )
                
        except ImportError as e:
            if "azure.identity" in str(e):
                raise ImportError(
                    "Azure Identity library is required for Entra ID authentication. "
                    "Install with: pip install azure-identity"
                )
            else:
                raise ImportError(
                    "OpenAI library is required. Install with: pip install openai>=1.0.0"
                )

    def generate_embedding(self, text: str) -> List[float]:
        """Generate Azure OpenAI embedding for text."""
        try:
            response = self.client.embeddings.create(
                model=self.deployment_name,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating Azure OpenAI embedding: {e}")
            raise RuntimeError(f"Azure OpenAI embedding generation failed: {e}")

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate Azure OpenAI embeddings for multiple texts in batch."""
        if not texts:
            return []
        
        try:
            # Azure OpenAI supports batch embedding generation
            response = self.client.embeddings.create(
                model=self.deployment_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating Azure OpenAI batch embeddings: {e}")
            # Fallback to individual embedding generation
            logger.warning("Falling back to individual embedding generation")
            return super().generate_embeddings_batch(texts)

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"azure-openai-{self.model}" 