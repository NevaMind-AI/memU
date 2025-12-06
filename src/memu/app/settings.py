from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from memu.prompts.memory_type import DEFAULT_MEMORY_TYPES
from memu.prompts.memory_type import PROMPTS as DEFAULT_MEMORY_TYPE_PROMPTS


def normalize_value(v: str) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return v


Normalize = BeforeValidator(normalize_value)


def _default_memory_types() -> list[str]:
    return list(DEFAULT_MEMORY_TYPES)


def _default_memory_type_prompts() -> dict[str, str]:
    return dict(DEFAULT_MEMORY_TYPE_PROMPTS)


def _default_memory_categories() -> list[dict[str, str]]:
    return [
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
    ]


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
        description="Which LLM client backend to use: 'httpx' (httpx) or 'sdk' (official OpenAI).",
    )
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (keys: 'chat'/'summary').",
    )


class EmbeddingConfig(BaseModel):
    provider: str = Field(
        default="openai",
        description="Identifier for the embedding provider implementation.",
    )
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="OPENAI_API_KEY")
    embed_model: str = Field(default="text-embedding-3-small")
    client_backend: str = Field(
        default="sdk",
        description="Which embedding client backend to use: 'httpx' (httpx) or 'sdk' (official OpenAI).",
    )
    batch_size: int = Field(
        default=25,
        description="Maximum batch size for embedding API calls. Some providers have limits (e.g., Bailian/DashScope: 10).",
    )
    endpoint_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (keys: 'embeddings'/'embed').",
    )


class BlobConfig(BaseModel):
    provider: str = Field(default="local")
    resources_dir: str = Field(default="./data/resources")


class DatabaseConfig(BaseModel):
    provider: str = Field(default="memory")


class RetrieveConfig(BaseModel):
    """Configure retrieval behavior for `MemoryUser.retrieve`.

    Attributes:
        method: Retrieval strategy. Use "rag" for embedding-based vector search or
            "llm" to delegate ranking to the LLM.
        top_k: Maximum number of results to return per category (and per stage),
            controlling breadth of the retrieved context.
    """

    method: Annotated[Literal["rag", "llm"], Normalize] = "rag"
    top_k: int = Field(
        default=5,
        description="Maximum number of results to return per category.",
    )


class MemorizeConfig(BaseModel):
    category_assign_threshold: float = Field(default=0.25)
    default_summary_prompt: str = Field(default="Summarize the text in one short paragraph.")
    summary_prompts: dict[str, str] = Field(
        default_factory=dict,
        description="Optional mapping of modality -> summary system prompt.",
    )
    memory_categories: list[dict[str, str]] = Field(
        default_factory=_default_memory_categories,
        description="Global memory category definitions embedded at service startup.",
    )
    category_summary_target_length: int = Field(
        default=400,
        description="Target max length for auto-generated category summaries.",
    )
    memory_types: list[str] = Field(
        default_factory=_default_memory_types,
        description="Ordered list of memory types (profile/event/knowledge/behavior by default).",
    )
    memory_type_prompts: dict[str, str] = Field(
        default_factory=_default_memory_type_prompts,
        description="System prompt overrides for each memory type extraction.",
    )


class DefaultUserModel(BaseModel):
    user_id: str | None = None


class UserConfig(BaseModel):
    model: type[BaseModel] = Field(default=DefaultUserModel)
