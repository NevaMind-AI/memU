from typing import Any

import httpx

from ..config import memorize_config
from .common import get_platform_memory_config


async def memorize(conversation_messages: list[dict[str, Any]]) -> str | None:
    config = get_platform_memory_config()
    payload = {
        "conversation": conversation_messages,
        "user_id": config.user_id,
        "agent_id": config.agent_id,
        "override_config": memorize_config,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{config.base_url}/api/v3/memory/memorize",
            headers={"Authorization": f"Bearer {config.api_key}"},
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        return result["task_id"]
