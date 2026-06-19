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
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    resource_url = data_dir / f"conv_{time_string}.json"
    with open(resource_url, "w") as f:
        json.dump(resource_data, f, indent=4, ensure_ascii=False)
    return data_dir.as_posix()


def memorize(conversation_messages: list[dict[str, Any]]) -> Awaitable[dict[str, Any]]:
    memory_service = get_memory_service()

    # Append the new conversation to the data folder, then incrementally sync the
    # whole folder; the input manifest ensures only the new file is processed.
    data_folder = dump_conversation_resource(conversation_messages)
    return memory_service.memorize(folder=data_folder, user={"user_id": USER_ID})
