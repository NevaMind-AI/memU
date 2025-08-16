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
        # self.model = kwargs.get("model", "text-embedding-ada-002")
        self.model = kwargs.get("model", "text-embedding-3-small")        

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
            api_key = kwargs.get("azure_api_key") or os.getenv("AZURE_API_KEY")
            endpoint = kwargs.get("azure_endpoint") or os.getenv("AZURE_ENDPOINT")
            api_version = kwargs.get("api_version", "2025-01-01-preview")

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
        # Support different types of custom embedding models
        custom_client = kwargs.get("client")
        
        if custom_client:
            # Direct client provided
            self.client = custom_client
            logger.info("Custom embedding client initialized with provided client")
        else:
            # Try to initialize based on model type and configuration
            model_type = kwargs.get("model_type", "").lower()
            model_name = kwargs.get("model_name") or self.model
            
            # Remove model_name from kwargs to avoid duplicate parameter error
            init_kwargs = {k: v for k, v in kwargs.items() if k != "model_name"}
            
            if model_type == "huggingface":
                self._init_huggingface_client(model_name, **init_kwargs)
            elif model_type == "sentence_transformers":
                self._init_sentence_transformers_client(model_name, **init_kwargs)
            elif model_type == "local":
                self._init_local_client(model_name, **init_kwargs)
            else:
                # Fallback: try to create sentence-transformers client
                try:
                    self._init_sentence_transformers_client(model_name, **init_kwargs)
                except Exception as e:
                    logger.warning(f"Failed to initialize default sentence-transformers client: {e}")
                    logger.warning("No custom embedding client provided or initialized")
                    
    def _init_huggingface_client(self, model_name: str, **kwargs):
        """Initialize HuggingFace Transformers embedding client"""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            device = kwargs.get("device", "cpu")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)
            model.to(device)
            
            # Create a wrapper client
            class HuggingFaceEmbeddingClient:
                def __init__(self, tokenizer, model, device="cpu"):
                    self.tokenizer = tokenizer
                    self.model = model
                    self.device = device
                    self.dimension = model.config.hidden_size
                    
                def embed(self, text: str) -> List[float]:
                    inputs = self.tokenizer(text, return_tensors="pt", 
                                          truncation=True, padding=True, 
                                          max_length=512)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        # Use mean pooling on last hidden states
                        embeddings = outputs.last_hidden_state.mean(dim=1)
                        return embeddings.squeeze().cpu().numpy().tolist()
                        
                def get_sentence_embedding_dimension(self):
                    return self.dimension
                    
            self.client = HuggingFaceEmbeddingClient(tokenizer, model, device)
            logger.info(f"HuggingFace embedding client initialized with model: {model_name}")
            
        except ImportError:
            logger.error("HuggingFace transformers or torch not installed. "
                        "Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace embedding client: {e}")
            raise
            
    def _init_sentence_transformers_client(self, model_name: str, **kwargs):
        """Initialize Sentence Transformers embedding client"""
        try:
            from sentence_transformers import SentenceTransformer
            
            device = kwargs.get("device", "cpu")
            model = SentenceTransformer(model_name, device=device)
            
            # Create a wrapper to standardize the interface
            class SentenceTransformersClient:
                def __init__(self, model):
                    self.model = model
                    self.dimension = model.get_sentence_embedding_dimension()
                    
                def embed(self, text: str) -> List[float]:
                    embedding = self.model.encode(text)
                    return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                    
                def encode(self, text: str):
                    return self.model.encode(text)
                    
                def get_sentence_embedding_dimension(self):
                    return self.dimension
                    
            self.client = SentenceTransformersClient(model)
            logger.info(f"Sentence Transformers embedding client initialized with model: {model_name}")
            
        except ImportError:
            logger.error("Sentence Transformers not installed. "
                        "Install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Sentence Transformers embedding client: {e}")
            raise
            
    def _init_local_client(self, model_path: str, **kwargs):
        """Initialize local embedding model client"""
        try:
            # Try to load as sentence-transformers model first
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer(model_path)
            
            class LocalEmbeddingClient:
                def __init__(self, model):
                    self.model = model
                    self.dimension = model.get_sentence_embedding_dimension()
                    
                def embed(self, text: str) -> List[float]:
                    embedding = self.model.encode(text)
                    return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                    
                def get_sentence_embedding_dimension(self):
                    return self.dimension
                    
            self.client = LocalEmbeddingClient(model)
            logger.info(f"Local embedding client initialized from path: {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize local embedding client from {model_path}: {e}")
            raise

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
            elif "text-embedding-3-small" in self.model:
                return 1536
            elif "text-embedding-3-large" in self.model:
                return 3072
            else:
                # Default for newer models
                return 1536
        elif self.provider == "custom":
            # Try to get dimension from client using various interfaces
            if hasattr(self.client, "get_sentence_embedding_dimension"):
                try:
                    return self.client.get_sentence_embedding_dimension()
                except Exception as e:
                    logger.warning(f"Failed to get dimension from get_sentence_embedding_dimension(): {e}")
            
            if hasattr(self.client, "dimension"):
                try:
                    return self.client.dimension
                except Exception as e:
                    logger.warning(f"Failed to get dimension from dimension attribute: {e}")
                    
            # Try to infer dimension by encoding a sample text
            try:
                sample_embedding = self.embed("sample text")
                if sample_embedding:
                    return len(sample_embedding)
            except Exception as e:
                logger.warning(f"Failed to infer dimension by sample embedding: {e}")
                
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

        # Custom with pre-built client
        from sentence_transformers import SentenceTransformer
        custom_model = SentenceTransformer('all-MiniLM-L6-v2')
        client = create_embedding_client('custom', client=custom_model)
        
        # Custom Sentence Transformers
        client = create_embedding_client('custom',
                                       model_type='sentence_transformers',
                                       model_name='all-MiniLM-L6-v2',
                                       device='cpu')
                                       
        # Custom HuggingFace
        client = create_embedding_client('custom',
                                       model_type='huggingface',
                                       model_name='bert-base-uncased',
                                       device='cuda')
                                       
        # Custom Local Model
        client = create_embedding_client('custom',
                                       model_type='local',
                                       model_name='/path/to/your/model')
    """
    return EmbeddingClient(provider, **kwargs)


def get_default_embedding_client() -> Optional[EmbeddingClient]:
    """
    Get a default embedding client based on available environment variables

    Supported Environment Variables:
        MEMU_EMBEDDING_PROVIDER: embedding provider ('openai', 'azure', 'custom')
        MEMU_EMBEDDING_MODEL: model name/path
        MEMU_EMBEDDING_MODEL_TYPE: for custom provider ('huggingface', 'sentence_transformers', 'local')
        MEMU_EMBEDDING_DEVICE: compute device for custom models ('cpu', 'cuda', etc.)
        
        OpenAI: OPENAI_API_KEY
        Azure: AZURE_API_KEY, AZURE_ENDPOINT
        
    Returns:
        EmbeddingClient if configuration is found, None otherwise
    """
    # Determine provider and model from environment
    embedding_provider = os.getenv("MEMU_EMBEDDING_PROVIDER", 
                                 os.getenv("MEMU_LLM_PROVIDER", "openai")).lower()
    embedding_model = os.getenv("MEMU_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Custom embedding specific configurations
    model_type = os.getenv("MEMU_EMBEDDING_MODEL_TYPE", "sentence_transformers")
    device = os.getenv("MEMU_EMBEDDING_DEVICE", "cpu")

    logger.info(f"Embedding provider: {embedding_provider}")
    logger.info(f"Embedding model: {embedding_model}")
    logger.info(f"Embedding model type: {model_type}")
    logger.info(f"Embedding device: {device}")

    # Try provider from env first
    if embedding_provider == "custom":
        try:
            return create_embedding_client(
                provider="custom", 
                model=embedding_model,
                model_type=model_type,
                model_name=embedding_model,
                device=device
            )
        except Exception as e:
            logger.warning(f"Failed to create custom embedding client: {e}")
    elif embedding_provider in ["openai", "azure"]:
        try:
            return create_embedding_client(embedding_provider, model=embedding_model)
        except Exception as e:
            logger.warning(f"Failed to create embedding client for provider {embedding_provider}: {e}")

    # Fallbacks
    if os.getenv("OPENAI_API_KEY"):
        try:
            return create_embedding_client("openai", model=embedding_model)
        except Exception as e:
            logger.warning(f"Failed to create OpenAI embedding client: {e}")

    if os.getenv("AZURE_API_KEY") and os.getenv("AZURE_ENDPOINT"):
        try:
            return create_embedding_client("azure", model=embedding_model)
        except Exception as e:
            logger.warning(f"Failed to create Azure OpenAI embedding client: {e}")

    logger.warning("No embedding client configuration found in environment variables")
    return None
