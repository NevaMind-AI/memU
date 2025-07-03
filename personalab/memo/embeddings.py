"""
Embedding module for conversation vectorization and semantic search.

Provides multiple embedding providers for converting conversations and messages
into vector representations for similarity search.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text.

        Args:
            text: Input text

        Returns:
            List[float]: Vector embedding
        """
        pass

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the name/identifier of the embedding model."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-ada-002 model.

    Requires OpenAI API key to be set in environment variables.
    """

    def __init__(
        self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"
    ):
        self.model = model
        self._dimension = 1536  # Ada-002 embedding dimension

        try:
            import os

            import openai

            # Check for API key
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
                )

            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

    def generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text."""
        try:
            response = self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating OpenAI embedding: {e}")
            raise RuntimeError(f"OpenAI embedding generation failed: {e}")

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"openai-{self.model}"


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Sentence Transformer embedding provider using Hugging Face models.

    Provides local embedding generation without API requirements.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name_str = model_name

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name)
            self._dimension = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError(
                "sentence-transformers package not installed. Install with: pip install sentence-transformers"
            )

    def generate_embedding(self, text: str) -> List[float]:
        """Generate sentence transformer embedding for text."""
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating sentence transformer embedding: {e}")
            raise RuntimeError(f"Sentence transformer embedding generation failed: {e}")

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"sentence-transformers-{self.model_name_str}"


class EmbeddingManager:
    """
    Manages embedding generation for conversations and messages.

    Provides high-level interface for generating embeddings with automatic
    provider selection and conversation-specific methods.
    """

    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    @property
    def model_name(self) -> str:
        return self.provider.model_name

    @property
    def embedding_dimension(self) -> int:
        return self.provider.embedding_dimension

    def generate_conversation_embedding(
        self, conversation: List[Dict[str, str]]
    ) -> List[float]:
        """
        Generate embedding for entire conversation.

        Args:
            conversation: List of message dictionaries

        Returns:
            List[float]: Conversation embedding
        """
        # Combine all message contents
        text_parts = []
        for message in conversation:
            role = message.get("role", "")
            content = message.get("content", "")
            text_parts.append(f"{role}: {content}")

        conversation_text = " ".join(text_parts)
        return self.provider.generate_embedding(conversation_text)

    def generate_message_embedding(self, message: Dict[str, str]) -> List[float]:
        """
        Generate embedding for individual message.

        Args:
            message: Message dictionary with 'role' and 'content'

        Returns:
            List[float]: Message embedding
        """
        content = message.get("content", "")
        return self.provider.generate_embedding(content)

    def generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for arbitrary text.

        Args:
            text: Input text

        Returns:
            List[float]: Text embedding
        """
        return self.provider.generate_embedding(text)


def create_embedding_manager(provider_type: str = "auto", **kwargs) -> EmbeddingManager:
    """
    Create embedding manager with specified provider.

    Args:
        provider_type: Type of provider ('auto', 'openai', 'sentence-transformers')
        **kwargs: Additional arguments for provider initialization

    Returns:
        EmbeddingManager: Configured embedding manager

    Raises:
        RuntimeError: If no suitable embedding provider can be initialized
    """
    if provider_type == "auto":
        # Try providers in order of preference
        errors = []

        try:
            provider = OpenAIEmbeddingProvider(**kwargs)
            print(f"Using OpenAI embedding provider: {provider.model_name}")
            return EmbeddingManager(provider)
        except Exception as e:
            errors.append(f"OpenAI: {e}")

        try:
            provider = SentenceTransformerProvider(**kwargs)
            print(f"Using Sentence Transformer provider: {provider.model_name}")
            return EmbeddingManager(provider)
        except Exception as e:
            errors.append(f"SentenceTransformer: {e}")

        # No providers available
        error_msg = "No embedding providers available. Errors: " + "; ".join(errors)
        raise RuntimeError(error_msg)

    elif provider_type == "openai":
        provider = OpenAIEmbeddingProvider(**kwargs)
        return EmbeddingManager(provider)

    elif provider_type == "sentence-transformers":
        provider = SentenceTransformerProvider(**kwargs)
        return EmbeddingManager(provider)

    else:
        raise ValueError(
            f"Unknown provider type: {provider_type}. Available: 'auto', 'openai', 'sentence-transformers'"
        )


__all__ = [
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "SentenceTransformerProvider",
    "EmbeddingManager",
    "create_embedding_manager",
]
