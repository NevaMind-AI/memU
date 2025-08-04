"""
Embedding Client for Memory Operations

This module provides embedding generation capabilities for memory content,
supporting different embedding providers like OpenAI, Azure OpenAI, etc.
"""

import os
import time
from typing import List, Optional

from ..utils import get_logger

logger = get_logger(__name__)


class EmbeddingClient:
    """
    Embedding client that supports multiple embedding providers.

    Supports:
    - OpenAI embeddings
    - Azure OpenAI embeddings
    - Local/custom embedding models
    """

    def __init__(self, provider: str = "openai", **kwargs):
        """
        Initialize embedding client

        Args:
            provider: Embedding provider ('openai', 'azure', 'custom')
            **kwargs: Provider-specific configuration
        """
        self.provider = provider.lower()
        self.client = None
        self.model = kwargs.get("model", "text-embedding-ada-002")

        # Initialize based on provider
        if self.provider == "openai":
            self._init_openai(**kwargs)
        elif self.provider == "azure":
            self._init_azure(**kwargs)
        elif self.provider == "custom":
            self._init_custom(**kwargs)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def _init_openai(self, **kwargs):
        """Initialize OpenAI embedding client"""
        try:
            import openai

            # Get API key from kwargs or environment
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not provided")

            self.client = openai.OpenAI(api_key=api_key)
            logger.info(f"OpenAI embedding client initialized with model: {self.model}")

        except ImportError:
            logger.error(
                "OpenAI library not installed. Install with: pip install openai"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    def _init_azure(self, **kwargs):
        """Initialize Azure OpenAI embedding client"""
        try:
            import openai

            # Required Azure parameters
            api_key = kwargs.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = kwargs.get("endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
            api_version = kwargs.get("api_version", "2023-05-15")

            if not api_key or not endpoint:
                raise ValueError("Azure OpenAI API key and endpoint are required")

            self.client = openai.AzureOpenAI(
                api_key=api_key, azure_endpoint=endpoint, api_version=api_version
            )

            # For Azure, model is the deployment name
            self.model = kwargs.get("deployment_name") or kwargs.get(
                "model", "text-embedding-ada-002"
            )

            logger.info(
                f"Azure OpenAI embedding client initialized with deployment: {self.model}"
            )

        except ImportError:
            logger.error(
                "OpenAI library not installed. Install with: pip install openai"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            raise

    def _init_custom(self, **kwargs):
        """Initialize custom embedding client"""
        # This is a placeholder for custom embedding implementations
        # Users can override this method or provide a custom client
        custom_client = kwargs.get("client")
        if custom_client:
            self.client = custom_client
            logger.info("Custom embedding client initialized")
        else:
            logger.warning("No custom embedding client provided")

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text

        Args:
            text: Text to embed

        Returns:
            List of float values representing the embedding vector
        """
        if not self.client:
            raise RuntimeError("Embedding client not initialized")

        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []

        try:
            if self.provider in ["openai", "azure"]:
                return self._embed_openai(text)
            elif self.provider == "custom":
                return self._embed_custom(text)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI/Azure OpenAI"""
        try:
            # Clean and prepare text
            text = text.replace("\n", " ").strip()
            if len(text) > 8000:  # OpenAI token limit approximation
                text = text[:8000]
                logger.warning("Text truncated to fit OpenAI token limit")

            response = self.client.embeddings.create(model=self.model, input=text)

            embedding = response.data[0].embedding
            logger.debug(f"Generated OpenAI embedding: {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            # Retry once after a short delay
            time.sleep(1)
            try:
                response = self.client.embeddings.create(model=self.model, input=text)
                return response.data[0].embedding
            except Exception as retry_e:
                logger.error(f"OpenAI embedding retry failed: {retry_e}")
                raise

    def _embed_custom(self, text: str) -> List[float]:
        """Generate embedding using custom client"""
        if hasattr(self.client, "embed"):
            return self.client.embed(text)
        elif hasattr(self.client, "get_embedding"):
            return self.client.get_embedding(text)
        elif hasattr(self.client, "encode"):
            # For sentence-transformers style interface
            embedding = self.client.encode(text)
            return (
                embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
            )
        else:
            raise RuntimeError(
                "Custom client does not have a supported embedding method"
            )

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        for text in texts:
            try:
                embedding = self.embed(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to embed text: {e}")
                # Add zero vector as placeholder
                embeddings.append([0.0] * 1536)  # Default OpenAI embedding size

        return embeddings

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this client"""
        if self.provider in ["openai", "azure"]:
            if "ada-002" in self.model:
                return 1536
            elif "ada-001" in self.model:
                return 1024
            else:
                # Default for newer models
                return 1536
        elif self.provider == "custom":
            # Try to get dimension from client
            if hasattr(self.client, "get_sentence_embedding_dimension"):
                return self.client.get_sentence_embedding_dimension()
            elif hasattr(self.client, "dimension"):
                return self.client.dimension
            else:
                return 1536  # Default fallback
        else:
            return 1536


def create_embedding_client(provider: str = "openai", **kwargs) -> EmbeddingClient:
    """
    Create an embedding client with the specified provider

    Args:
        provider: Embedding provider ('openai', 'azure', 'custom')
        **kwargs: Provider-specific configuration

    Returns:
        EmbeddingClient instance

    Examples:
        # OpenAI
        client = create_embedding_client('openai', api_key='your-key')

        # Azure OpenAI
        client = create_embedding_client('azure',
                                       api_key='your-key',
                                       endpoint='your-endpoint',
                                       deployment_name='your-deployment')

        # Custom
        custom_model = SentenceTransformer('all-MiniLM-L6-v2')
        client = create_embedding_client('custom', client=custom_model)
    """
    return EmbeddingClient(provider, **kwargs)


def get_default_embedding_client() -> Optional[EmbeddingClient]:
    """
    Get a default embedding client based on available environment variables

    Returns:
        EmbeddingClient if configuration is found, None otherwise
    """
    # Try OpenAI first
    if os.getenv("OPENAI_API_KEY"):
        try:
            return create_embedding_client("openai")
        except Exception as e:
            logger.warning(f"Failed to create OpenAI embedding client: {e}")

    # Try Azure OpenAI
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        try:
            return create_embedding_client("azure")
        except Exception as e:
            logger.warning(f"Failed to create Azure OpenAI embedding client: {e}")

    logger.warning("No embedding client configuration found in environment variables")
    return None
