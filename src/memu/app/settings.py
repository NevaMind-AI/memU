from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, RootModel, StringConstraints, model_validator


def normalize_value(v: str) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return v


Normalize = BeforeValidator(normalize_value)


class EmbeddingConfig(BaseModel):
    """Configuration for an embedding (vectorization) model client.

    Defaults to OpenAI's ``text-embedding-3-small``; embedding-only providers
    (Jina, Voyage) bring their own ``base_url``/``api_key`` via provider defaults
    (see ``memu.embedding.defaults``).
    """

    provider: str = Field(
        default="openai",
        description="Identifier for the embedding provider implementation (used by HTTP client backend).",
    )
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="OPENAI_API_KEY")
    embed_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model used for vectorization.",
    )
    embed_batch_size: int = Field(
        default=1,
        description="Maximum batch size for embedding API calls (used by the SDK client backend).",
    )
    client_backend: str = Field(
        default="sdk",
        description=(
            "Which embedding client backend to use: 'sdk' (official OpenAI SDK) or "
            "'httpx' (raw HTTP, supports all providers in memu.embedding.backends, "
            "e.g. openai/jina/voyage/doubao/openrouter)."
        ),
    )
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (key: 'embeddings').",
    )

    @model_validator(mode="after")
    def set_provider_defaults(self) -> "EmbeddingConfig":
        # Each field is only overridden while it still holds the OpenAI default,
        # so explicit values survive.
        from memu.embedding.defaults import EMBEDDING_PROVIDER_ENDPOINTS, default_embedding_model

        endpoint = EMBEDDING_PROVIDER_ENDPOINTS.get(self.provider)
        if endpoint is not None:
            base_url, api_key = endpoint
            if self.base_url == "https://api.openai.com/v1":
                self.base_url = base_url
            if self.api_key == "OPENAI_API_KEY":
                self.api_key = api_key
        if self.embed_model == "text-embedding-3-small":
            resolved = default_embedding_model(self.provider)
            if resolved is not None:
                self.embed_model = resolved
        return self


class RetrieveResourceConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether to enable resource retrieval.")
    top_k: int = Field(default=5, description="Total number of resources to retrieve.")


class RetrieveFileConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether to enable file retrieval.")
    top_k: int = Field(default=5, description="Total number of files to retrieve.")
    tracks: list[str] | None = Field(
        default=None,
        description="Optional file tracks (e.g. ['memory', 'skill']) to filter on. None means all tracks.",
    )


class ProgressiveRetrieveConfig(BaseModel):
    """Configure the single-shot, LLM-free retrieval (``progressive_retrieve``).

    The query is embedded once and the file-segment and resource layers are each
    ranked by vector similarity. No routing, sufficiency check, or summarization
    is involved.
    """

    file: RetrieveFileConfig = Field(default=RetrieveFileConfig())
    resource: RetrieveResourceConfig = Field(default=RetrieveResourceConfig())


class DefaultUserModel(BaseModel):
    user_id: str | None = None
    # Agent/session scoping for multi-agent and multi-session memory filtering
    agent_id: str | None = None


class UserConfig(BaseModel):
    model: type[BaseModel] = Field(default=DefaultUserModel)


Key = Annotated[str, StringConstraints(min_length=1)]


class EmbeddingProfilesConfig(RootModel[dict[Key, EmbeddingConfig]]):
    """Named embedding profiles keyed by profile name.

    A ``default`` profile is always present, and an ``embedding`` alias falls
    back to ``default`` so callers can address the vectorization profile
    explicitly.
    """

    root: dict[str, EmbeddingConfig] = Field(default_factory=lambda: {"default": EmbeddingConfig()})

    def get(self, key: str, default: EmbeddingConfig | None = None) -> EmbeddingConfig | None:
        return self.root.get(key, default)

    @model_validator(mode="before")
    @classmethod
    def ensure_default(cls, data: Any) -> Any:
        if data is None:
            data = {}
        elif isinstance(data, dict):
            data = dict(data)
        else:
            return data
        if "default" not in data:
            data["default"] = EmbeddingConfig()
        if "embedding" not in data:
            data["embedding"] = data["default"]
        return data

    @property
    def profiles(self) -> dict[str, EmbeddingConfig]:
        return self.root

    @property
    def default(self) -> EmbeddingConfig:
        return self.root.get("default", EmbeddingConfig())


class MetadataStoreConfig(BaseModel):
    provider: Annotated[Literal["inmemory", "postgres", "sqlite"], Normalize] = "inmemory"
    ddl_mode: Annotated[Literal["create", "validate"], Normalize] = "create"
    dsn: str | None = Field(default=None, description="Database connection string (required for postgres/sqlite).")


class VectorIndexConfig(BaseModel):
    provider: Annotated[Literal["bruteforce", "pgvector", "none"], Normalize] = "bruteforce"
    dsn: str | None = Field(default=None, description="Postgres connection string when provider=pgvector.")


class DatabaseConfig(BaseModel):
    metadata_store: MetadataStoreConfig = Field(default_factory=MetadataStoreConfig)
    vector_index: VectorIndexConfig | None = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        if self.vector_index is None:
            if self.metadata_store.provider == "postgres":
                self.vector_index = VectorIndexConfig(provider="pgvector", dsn=self.metadata_store.dsn)
            else:
                self.vector_index = VectorIndexConfig(provider="bruteforce")
        elif self.vector_index.provider == "pgvector" and self.vector_index.dsn is None:
            self.vector_index = self.vector_index.model_copy(update={"dsn": self.metadata_store.dsn})
