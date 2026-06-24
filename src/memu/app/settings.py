from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, RootModel, StringConstraints, model_validator

from memu.prompts.category_summary import (
    DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL,
)
from memu.prompts.category_summary import (
    PROMPT as CATEGORY_SUMMARY_PROMPT,
)
from memu.prompts.memory_type import (
    DEFAULT_MEMORY_CUSTOM_PROMPT_ORDINAL,
    DEFAULT_MEMORY_TYPES,
)
from memu.prompts.memory_type import (
    PROMPTS as DEFAULT_MEMORY_TYPE_PROMPTS,
)


def normalize_value(v: str) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return v


Normalize = BeforeValidator(normalize_value)


def _default_memory_types() -> list[str]:
    return list(DEFAULT_MEMORY_TYPES)


def _default_memory_type_prompts() -> "dict[str, str | CustomPrompt]":
    return dict(DEFAULT_MEMORY_TYPE_PROMPTS)


class PromptBlock(BaseModel):
    label: str | None = None
    ordinal: int = Field(default=0)
    prompt: str | None = None


class CustomPrompt(RootModel[dict[str, PromptBlock]]):
    root: dict[str, PromptBlock] = Field(default_factory=dict)

    def get(self, key: str, default: PromptBlock | None = None) -> PromptBlock | None:
        return self.root.get(key, default)

    def items(self) -> list[tuple[str, PromptBlock]]:
        return list(self.root.items())


def complete_prompt_blocks(prompt: CustomPrompt, default_blocks: Mapping[str, int]) -> CustomPrompt:
    for key, ordinal in default_blocks.items():
        if key not in prompt.root:
            prompt.root[key] = PromptBlock(ordinal=ordinal)
    return prompt


CompleteMemoryTypePrompt = AfterValidator(lambda v: complete_prompt_blocks(v, DEFAULT_MEMORY_CUSTOM_PROMPT_ORDINAL))


CompleteCategoryPrompt = AfterValidator(lambda v: complete_prompt_blocks(v, DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL))


class CategoryConfig(BaseModel):
    name: str
    description: str = ""
    target_length: int | None = None
    summary_prompt: str | Annotated[CustomPrompt, CompleteCategoryPrompt] | None = None


class LazyLLMSource(BaseModel):
    source: str | None = Field(default=None, description="default source for lazyllm client backend")
    llm_source: str | None = Field(default=None, description="LLM source for lazyllm client backend")
    embed_source: str | None = Field(default=None, description="Embedding source for lazyllm client backend")
    vlm_source: str | None = Field(default=None, description="VLM source for lazyllm client backend")
    stt_source: str | None = Field(default=None, description="STT source for lazyllm client backend")
    vlm_model: str = Field(default="qwen-vl-plus", description="Vision language model for lazyllm client backend")
    stt_model: str = Field(default="qwen-audio-turbo", description="Speech-to-text model for lazyllm client backend")


# Per-provider defaults: provider -> (base_url, api_key_env_or_value, chat_model).
# Used by ``LLMConfig.set_provider_defaults`` to swap OpenAI defaults when a provider is selected.
# Each provider defaults to its latest small/fast model (verified June 2026).
_PROVIDER_DEFAULTS: dict[str, tuple[str, str, str]] = {
    "grok": ("https://api.x.ai/v1", "XAI_API_KEY", "grok-4-1-fast"),
    "claude": ("https://api.anthropic.com", "ANTHROPIC_API_KEY", "claude-haiku-4-5"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "deepseek-v4-flash"),
    "kimi": ("https://api.moonshot.cn/v1", "MOONSHOT_API_KEY", "kimi-k2.7-code-highspeed"),
    "minimax": ("https://api.minimax.io/v1", "MINIMAX_API_KEY", "MiniMax-M3"),
    "doubao": ("https://ark.cn-beijing.volces.com", "ARK_API_KEY", "doubao-seed-2.0-lite"),
    "openrouter": ("https://openrouter.ai", "OPENROUTER_API_KEY", "openai/gpt-5.4-mini"),
}


class LLMConfig(BaseModel):
    provider: str = Field(
        default="openai",
        description="Identifier for the LLM provider implementation (used by HTTP client backend).",
    )
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="OPENAI_API_KEY")
    chat_model: str = Field(default="gpt-5.4-mini")
    client_backend: str = Field(
        default="sdk",
        description=(
            "Which LLM client backend to use: 'sdk' (official OpenAI SDK), "
            "'anthropic' (official Anthropic/Claude SDK), 'httpx' (raw HTTP, supports "
            "all providers in memu.llm.backends), or 'lazyllm_backend' (Qwen, Doubao, "
            "SiliconFlow, etc.)."
        ),
    )
    lazyllm_source: LazyLLMSource = Field(default=LazyLLMSource())
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (keys: 'chat'/'summary').",
    )
    # Backward-compat bridge: embedding is owned by the dedicated
    # ``memu.embedding`` clients (``EmbeddingConfig``/``embedding_profiles``). The
    # LLM/chat clients no longer embed. These fields are only consumed by
    # ``embedding_config_from_llm`` to derive an embedding profile from an LLM
    # profile when no explicit ``embedding_profiles`` is supplied. Prefer setting
    # ``embedding_profiles`` directly.
    embed_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model used to derive an embedding profile from this LLM profile (bridge only).",
    )
    embed_batch_size: int = Field(
        default=1,
        description="Embedding batch size used to derive an embedding profile from this LLM profile (bridge only).",
    )

    @model_validator(mode="after")
    def set_provider_defaults(self) -> "LLMConfig":
        # Per-provider defaults for the HTTP client backend. Each entry only
        # overrides a field when it still holds the OpenAI default, so explicit
        # user values are always preserved.
        defaults = _PROVIDER_DEFAULTS.get(self.provider)
        if defaults is not None:
            base_url, api_key, chat_model = defaults
            if self.base_url == "https://api.openai.com/v1":
                self.base_url = base_url
            if self.api_key == "OPENAI_API_KEY":
                self.api_key = api_key
            if self.chat_model == "gpt-5.4-mini":
                self.chat_model = chat_model
        return self


class VLMConfig(BaseModel):
    """Configuration for a vision-language (multimodal) model client.

    Sibling to :class:`LLMConfig` but scoped to the ``vision`` capability used by
    image/video preprocessing. Defaults to each provider's latest VLM model (see
    ``memu.vlm.VLM_PROVIDER_DEFAULTS``) instead of the small/fast chat default.
    """

    provider: str = Field(
        default="openai",
        description="Identifier for the VLM provider implementation (used by HTTP client backend).",
    )
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="OPENAI_API_KEY")
    vlm_model: str = Field(default="gpt-5.4", description="Vision-language model used for image/video understanding.")
    client_backend: str = Field(
        default="sdk",
        description=(
            "Which VLM client backend to use: 'sdk' (official OpenAI SDK), "
            "'anthropic' (official Anthropic/Claude SDK), or 'httpx' (raw HTTP, "
            "supports all providers in memu.vlm.backends)."
        ),
    )
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (key: 'vision').",
    )

    @model_validator(mode="after")
    def set_provider_defaults(self) -> "VLMConfig":
        # base_url/api_key reuse the shared per-provider HTTP defaults; vlm_model
        # comes from the VLM-specific defaults. Each field is only overridden
        # while it still holds the OpenAI default, so explicit values survive.
        from memu.vlm.defaults import default_vlm_model

        defaults = _PROVIDER_DEFAULTS.get(self.provider)
        if defaults is not None:
            base_url, api_key, _chat_model = defaults
            if self.base_url == "https://api.openai.com/v1":
                self.base_url = base_url
            if self.api_key == "OPENAI_API_KEY":
                self.api_key = api_key
        if self.vlm_model == "gpt-5.4":
            resolved = default_vlm_model(self.provider)
            if resolved is not None:
                self.vlm_model = resolved
        return self


def vlm_config_from_llm(llm: "LLMConfig") -> "VLMConfig":
    """Derive a :class:`VLMConfig` from an :class:`LLMConfig`.

    Reuses the LLM provider/credentials/transport so vision steps work with zero
    extra configuration, swapping only the model for the provider's latest VLM
    (falling back to the LLM chat model when the provider has no known VLM).
    """
    from memu.vlm.defaults import default_vlm_model

    # The anthropic SDK backend leaves ``provider`` at its generic default, so
    # map it explicitly to resolve the right VLM model.
    provider = "claude" if llm.client_backend == "anthropic" else llm.provider
    vlm_model = default_vlm_model(provider) or llm.chat_model
    return VLMConfig(
        provider=provider,
        base_url=llm.base_url,
        api_key=llm.api_key,
        vlm_model=vlm_model,
        client_backend=llm.client_backend,
        endpoint_overrides=dict(llm.endpoint_overrides),
    )


class EmbeddingConfig(BaseModel):
    """Configuration for an embedding (vectorization) model client.

    Sibling to :class:`LLMConfig`/:class:`VLMConfig` but scoped to the embedding
    capability used by vector search. Defaults to OpenAI's
    ``text-embedding-3-small``; embedding-only providers (Jina, Voyage) bring
    their own ``base_url``/``api_key`` via provider defaults (see
    ``memu.embedding.defaults``).
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
            "Which embedding client backend to use: 'sdk' (official OpenAI SDK), "
            "'httpx' (raw HTTP, supports all providers in memu.embedding.backends, "
            "e.g. openai/jina/voyage/doubao/openrouter), or 'lazyllm_backend'."
        ),
    )
    lazyllm_source: LazyLLMSource = Field(default=LazyLLMSource())
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (key: 'embeddings').",
    )

    @model_validator(mode="after")
    def set_provider_defaults(self) -> "EmbeddingConfig":
        from memu.embedding.defaults import EMBEDDING_PROVIDER_ENDPOINTS, default_embedding_model

        # base_url/api_key: reuse the shared chat per-provider defaults when the
        # provider is also a chat provider; otherwise fall back to the
        # embedding-only endpoint table (Jina, Voyage). Each field is only
        # overridden while it still holds the OpenAI default, so explicit values
        # survive.
        endpoint = _PROVIDER_DEFAULTS.get(self.provider)
        base_url = endpoint[0] if endpoint is not None else None
        api_key = endpoint[1] if endpoint is not None else None
        if base_url is None:
            embed_endpoint = EMBEDDING_PROVIDER_ENDPOINTS.get(self.provider)
            if embed_endpoint is not None:
                base_url, api_key = embed_endpoint
        if base_url is not None and self.base_url == "https://api.openai.com/v1":
            self.base_url = base_url
        if api_key is not None and self.api_key == "OPENAI_API_KEY":
            self.api_key = api_key
        if self.embed_model == "text-embedding-3-small":
            resolved = default_embedding_model(self.provider)
            if resolved is not None:
                self.embed_model = resolved
        return self


def embedding_config_from_llm(llm: "LLMConfig") -> "EmbeddingConfig":
    """Derive an :class:`EmbeddingConfig` from an :class:`LLMConfig`.

    Reuses the LLM provider/credentials/transport/embed model so vectorization
    works with zero extra configuration when no dedicated embedding profile is
    supplied. The ``anthropic`` transport has no embeddings API; the derived
    config preserves that so the embedding gateway raises a clear error.
    """
    return EmbeddingConfig(
        provider=llm.provider,
        base_url=llm.base_url,
        api_key=llm.api_key,
        embed_model=llm.embed_model,
        embed_batch_size=llm.embed_batch_size,
        client_backend=llm.client_backend,
        lazyllm_source=llm.lazyllm_source,
        endpoint_overrides=dict(llm.endpoint_overrides),
    )


class BlobConfig(BaseModel):
    provider: str = Field(default="local")
    resources_dir: str = Field(default="./data/resources")


class MemoryFilesConfig(BaseModel):
    """Render structured memory into a browsable markdown "memory file system".

    Purely additive and read-only against the store; disabled by default so it
    never changes existing memorize/retrieve behavior. When enabled, the tree is
    refreshed by ``memorize_workspace`` (and on demand via ``export_memory_files``).
    """

    enabled: bool = Field(
        default=False,
        description="Enable rendering structured memory into browsable markdown files.",
    )
    output_dir: str = Field(
        default="./data/memory",
        description=(
            "Directory where the memory markdown tree (the INDEX.md/MEMORY.md/SKILL.md root "
            "indexes plus the resource/, memory/, and skill/ directories) is written."
        ),
    )
    synthesize: bool = Field(
        default=False,
        description=(
            "Synthesize MEMORY.md and skill docs from per-source descriptions via the LLM "
            "instead of rendering already-extracted records. INDEX.md stays deterministic."
        ),
    )
    synthesis_llm_profile: str = Field(
        default="default",
        description="LLM profile used when synthesize=True.",
    )


class RetrieveCategoryConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether to enable category retrieval.")
    top_k: int = Field(default=5, description="Total number of categories to retrieve.")


class RetrieveItemConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether to enable item retrieval.")
    top_k: int = Field(default=5, description="Total number of items to retrieve.")
    # Reference-aware retrieval
    use_category_references: bool = Field(
        default=False,
        description="When category retrieval is insufficient, follow [ref:ITEM_ID] citations to fetch referenced items.",
    )
    # Salience-aware retrieval settings
    ranking: Literal["similarity", "salience"] = Field(
        default="similarity",
        description="Ranking strategy: 'similarity' (cosine only) or 'salience' (weighted by reinforcement + recency).",
    )
    recency_decay_days: float = Field(
        default=30.0,
        description="Half-life in days for recency decay in salience scoring. After this many days, recency factor is ~0.5.",
    )


class RetrieveResourceConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether to enable resource retrieval.")
    top_k: int = Field(default=5, description="Total number of resources to retrieve.")


class RetrieveConfig(BaseModel):
    """Configure retrieval behavior for `MemoryUser.retrieve`.

    Attributes:
        method: Retrieval strategy. Use "rag" for embedding-based vector search or
            "llm" to delegate ranking to the LLM.
        top_k: Maximum number of results to return per category (and per stage),
            controlling breadth of the retrieved context.
    """

    method: Annotated[Literal["rag", "llm"], Normalize] = "rag"
    # top_k: int = Field(
    #     default=5,
    #     description="Maximum number of results to return per category.",
    # )
    route_intention: bool = Field(
        default=True, description="Whether to route intention (judge needs retrieval & rewrite query)."
    )
    # route_intention_prompt: str = Field(default="", description="User prompt for route intention.")
    # route_intention_llm_profile: str = Field(default="default", description="LLM profile for route intention.")
    category: RetrieveCategoryConfig = Field(default=RetrieveCategoryConfig())
    item: RetrieveItemConfig = Field(default=RetrieveItemConfig())
    resource: RetrieveResourceConfig = Field(default=RetrieveResourceConfig())
    sufficiency_check: bool = Field(default=True, description="Whether to check sufficiency after each tier.")
    sufficiency_check_prompt: str = Field(default="", description="User prompt for sufficiency check.")
    sufficiency_check_llm_profile: str = Field(default="default", description="LLM profile for sufficiency check.")
    llm_ranking_llm_profile: str = Field(default="default", description="LLM profile for LLM ranking.")


class MemorizeConfig(BaseModel):
    category_assign_threshold: float = Field(default=0.25)
    multimodal_preprocess_prompts: dict[str, str | CustomPrompt] = Field(
        default_factory=dict,
        description="Optional mapping of modality -> preprocess system prompt.",
    )
    preprocess_llm_profile: str = Field(default="default", description="LLM profile for preprocess.")
    vlm_profile: str = Field(
        default="default",
        description="LLM profile whose provider/credentials back the VLM client used for image/video vision.",
    )
    memory_types: list[str] = Field(
        default_factory=_default_memory_types,
        description="Ordered list of memory types (profile/event/knowledge/behavior by default).",
    )
    memory_type_prompts: dict[str, str | Annotated[CustomPrompt, CompleteMemoryTypePrompt]] = Field(
        default_factory=_default_memory_type_prompts,
        description="User prompt overrides for each memory type extraction.",
    )
    memory_extract_llm_profile: str = Field(default="default", description="LLM profile for memory extract.")
    memory_categories: list[CategoryConfig] = Field(
        default_factory=list,
        description=(
            "Optional seed categories. The kernel presets no taxonomy: categories are "
            "discovered adaptively from ingested content. Provide seeds only to guide "
            "(not constrain) the taxonomy; an empty list means fully open/adaptive."
        ),
    )
    # default_category_summary_prompt: str | CustomPrompt = Field(
    default_category_summary_prompt: str | Annotated[CustomPrompt, CompleteCategoryPrompt] = Field(
        default=CATEGORY_SUMMARY_PROMPT,
        description="Default system prompt for auto-generated category summaries.",
    )
    default_category_summary_target_length: int = Field(
        default=400,
        description="Target max length for auto-generated category summaries.",
    )
    category_update_llm_profile: str = Field(default="default", description="LLM profile for category summary.")
    # Reference tracking for category summaries
    enable_item_references: bool = Field(
        default=False,
        description="Enable inline [ref:ITEM_ID] citations in category summaries linking to source memory items.",
    )
    enable_item_reinforcement: bool = Field(
        default=False,
        description="Enable reinforcement tracking for memory items.",
    )


class PatchConfig(BaseModel):
    pass


class DefaultUserModel(BaseModel):
    user_id: str | None = None
    # Agent/session scoping for multi-agent and multi-session memory filtering
    # agent_id: str | None = None
    # session_id: str | None = None


class UserConfig(BaseModel):
    model: type[BaseModel] = Field(default=DefaultUserModel)


Key = Annotated[str, StringConstraints(min_length=1)]


class LLMProfilesConfig(RootModel[dict[Key, LLMConfig]]):
    root: dict[str, LLMConfig] = Field(default_factory=lambda: {"default": LLMConfig()})

    def get(self, key: str, default: LLMConfig | None = None) -> LLMConfig | None:
        return self.root.get(key, default)

    @model_validator(mode="before")
    @classmethod
    def ensure_default(cls, data: Any) -> Any:
        # if data is None:
        #     return {"default": LLMConfig()}
        # if isinstance(data, dict) and "default" not in data:
        #     data = dict(data)
        #     data["default"] = LLMConfig()
        # return data
        if data is None:
            data = {}
        elif isinstance(data, dict):
            data = dict(data)
        else:
            return data
        if "default" not in data:
            data["default"] = LLMConfig()
        if "embedding" not in data:
            data["embedding"] = data["default"]
        return data

    @property
    def profiles(self) -> dict[str, LLMConfig]:
        return self.root

    @property
    def default(self) -> LLMConfig:
        return self.root.get("default", LLMConfig())


class EmbeddingProfilesConfig(RootModel[dict[Key, EmbeddingConfig]]):
    """Named embedding profiles, mirroring :class:`LLMProfilesConfig`.

    When no explicit embedding profiles are supplied, the service derives them
    from the LLM profiles (see ``embedding_config_from_llm``) so existing
    configs keep vectorizing through the same provider/credentials.
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
