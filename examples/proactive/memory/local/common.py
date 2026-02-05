import os

from memu.app import MemoryService

from ..config import memorize_config, retrieve_config

USER_ID = "claude_user"
SHARED_MEMORY_SERVICE = None


def get_memory_service() -> MemoryService:
    global SHARED_MEMORY_SERVICE
    if SHARED_MEMORY_SERVICE is not None:
        return SHARED_MEMORY_SERVICE

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    SHARED_MEMORY_SERVICE = MemoryService(
        llm_profiles={
            "default": {
                "api_key": api_key,
                "chat_model": "gpt-4o-mini",
            },
        },
        memorize_config=memorize_config,
        retrieve_config=retrieve_config,
    )
    return SHARED_MEMORY_SERVICE
