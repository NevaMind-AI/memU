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


def _default_memory_categories() -> list[CategoryConfig]:
    return [
        CategoryConfig.model_validate(cat)
        for cat in (
            {"name": "personal_info", "description": "Personal information about the user"},
            {"name": "preferences", "description": "User preferences, likes and dislikes"},
            {"name": "relationships", "description": "Information about relationships with others"},
            {"name": "activities", "description": "Activities, hobbies, and interests"},
            {"name": "goals", "description": "Goals, aspirations, and objectives"},
            {"name": "experiences", "description": "Past experiences and events"},
            {"name": "knowledge", "description": "Knowledge, facts, and learned information"},
            {"name": "opinions", "description": "Opinions, viewpoints, and perspectives"},
            {"name": "habits", "description": "Habits, routines, and patterns"},
            {"name": "work_life", "description": "Work-related information and professional life"},
        )
    ]


class LazyLLMSource(BaseModel):
    source: str | None = Field(default=None, description="default source for lazyllm client backend")
    llm_source: str | None = Field(default=None, description="LLM source for lazyllm client backend")
    embed_source: str | None = Field(default=None, description="Embedding source for lazyllm client backend")
    vlm_source: str | None = Field(default=None, description="VLM source for lazyllm client backend")
    stt_source: str | None = Field(default=None, description="STT source for lazyllm client backend")
    vlm_model: str = Field(default="qwen-vl-plus", description="Vision language model for lazyllm client backend")
    stt_model: str = Field(default="qwen-audio-turbo", description="Speech-to-text model for lazyllm client backend")


class LLMConfig(BaseModel):
    provider: str = Field(
        default="openai",
        description="Identifier for the LLM provider implementation (used by HTTP client backend).",
    )
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="OPENAI_API_KEY")
    chat_model: str = Field(default="gpt-4o-mini")
    client_backend: str = Field(
        default="sdk",
        description="Which LLM client backend to use: 'httpx' (httpx), 'sdk' (official OpenAI), or 'lazyllm_backend' (for more LLM source like Qwen, Doubao, SIliconflow, etc.)",
    )
    lazyllm_source: LazyLLMSource = Field(default=LazyLLMSource())
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (keys: 'chat'/'summary').",
    )
    embed_model: str = Field(
        default="text-embedding-3-small",
        description="Default embedding model used for vectorization.",
    )
    embed_batch_size: int = Field(
        default=1,
        description="Maximum batch size for embedding API calls (used by SDK client backends).",
    )

    @model_validator(mode="after")
    def set_provider_defaults(self) -> "LLMConfig":
        if self.provider == "grok":
            # If values match the OpenAI defaults, switch them to Grok defaults
            if self.base_url == "https://api.openai.com/v1":
                self.base_url = "https://api.x.ai/v1"
            if self.api_key == "OPENAI_API_KEY":
                self.api_key = "XAI_API_KEY"
            if self.chat_model == "gpt-4o-mini":
                self.chat_model = "grok-2-latest"
        return self


class BlobConfig(BaseModel):
    provider: str = Field(default="local")
    resources_dir: str = Field(default="./data/resources")


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
        default_factory=_default_memory_categories,
        description="Global memory category definitions embedded at service startup.",
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
