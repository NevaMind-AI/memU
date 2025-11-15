from pydantic import BaseModel, Field

from memu.prompts.memory_type import DEFAULT_MEMORY_TYPES
from memu.prompts.memory_type import PROMPTS as DEFAULT_MEMORY_TYPE_PROMPTS


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


class AppSettings(BaseModel):
    # where to store raw resources
    resources_dir: str = Field(default="./resources")
    # openai base
    openai_base: str = Field(default="https://api.openai.com/v1")
    openai_api_key: str = Field(default="OPENAI_API_KEY")
    # models
    chat_model: str = Field(default="gpt-5-nano")
    embed_model: str = Field(default="text-embedding-3-small")
    llm_client_backend: str = Field(
        default="sdk",
        description="Which OpenAI client backend to use: 'httpx' (httpx) or 'sdk' (official OpenAI).",
    )
    llm_http_provider: str = Field(
        default="openai",
        description="Name of the HTTP LLM provider implementation (e.g. 'openai').",
    )
    llm_http_endpoints: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides for HTTP endpoints (keys: 'chat'/'summary', 'embeddings'/'embed').",
    )
    # thresholds
    category_assign_threshold: float = Field(default=0.25)
    # summarization prompts
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
