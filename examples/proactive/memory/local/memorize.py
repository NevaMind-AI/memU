import json
import os
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

import pendulum

from memu.app import MemoryService

from ..config import memorize_config

USER_ID = "claude_user"


def dump_conversation_resource(
    conversation_messages: list[dict[str, Any]],
) -> str:
    resource_data = {
        "content": [
            {
                "role": message.get("role", "system"),
                "content": {"text": message.get("content", "")},
                "created_at": message.get("timestamp", pendulum.now().isoformat()),
            }
            for message in conversation_messages
        ]
    }
    time_string = pendulum.now().format("YYYYMMDD_HHmmss")
    resource_url = Path(__file__).parent / "data" / f"conv_{time_string}.json"
    with open(resource_url, "w") as f:
        json.dump(resource_data, f, indent=4, ensure_ascii=False)
    return resource_url.as_posix()


def memorize(conversation_messages: list[dict[str, Any]]) -> Awaitable[dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    memory_service = MemoryService(
        llm_profiles={
            "default": {
                "api_key": api_key,
                "chat_model": "gpt-4o-mini",
            },
        },
        memorize_config=memorize_config,
    )

    resource_url = dump_conversation_resource(conversation_messages)
    return memory_service.memorize(resource_url=resource_url, modality="conversation", user={"user_id": USER_ID})
