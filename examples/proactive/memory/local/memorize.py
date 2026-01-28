import json
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

import pendulum

from .common import get_memory_service

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
    resource_url.parent.mkdir(parents=True, exist_ok=True)
    with open(resource_url, "w") as f:
        json.dump(resource_data, f, indent=4, ensure_ascii=False)
    return resource_url.as_posix()


def memorize(conversation_messages: list[dict[str, Any]]) -> Awaitable[dict[str, Any]]:
    memory_service = get_memory_service()

    resource_url = dump_conversation_resource(conversation_messages)
    return memory_service.memorize(resource_url=resource_url, modality="conversation", user={"user_id": USER_ID})
