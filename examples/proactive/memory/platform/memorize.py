from typing import Any

import aiohttp

from ..config import memorize_config

BASE_URL = "https://api.memu.so"
API_KEY = "your memu api key"
USER_ID = "claude_user"
AGENT_ID = "claude_agent"


async def memorize(conversation_messages: list[dict[str, Any]]) -> str | None:
    payload = {
        "conversation": conversation_messages,
        "user_id": USER_ID,
        "agent_id": AGENT_ID,
        "override_config": memorize_config,
    }

    async with (
        aiohttp.ClientSession() as session,
        session.post(
            f"{BASE_URL}/api/v3/memory/memorize",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json=payload,
        ) as response,
    ):
        result = await response.json()
        task_id = result["task_id"]
        return task_id
