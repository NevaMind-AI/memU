from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformMemoryConfig:
    base_url: str
    api_key: str
    user_id: str
    agent_id: str


def get_platform_memory_config() -> PlatformMemoryConfig:
    api_key = os.getenv("MEMU_API_KEY", "").strip()
    if not api_key:
        msg = "Please set MEMU_API_KEY for the platform proactive example"
        raise ValueError(msg)

    base_url = os.getenv("MEMU_BASE_URL", "https://api.memu.so").strip().rstrip("/")
    user_id = os.getenv("MEMU_USER_ID", "claude_user").strip() or "claude_user"
    agent_id = os.getenv("MEMU_AGENT_ID", "claude_agent").strip() or "claude_agent"

    return PlatformMemoryConfig(
        base_url=base_url or "https://api.memu.so",
        api_key=api_key,
        user_id=user_id,
        agent_id=agent_id,
    )
