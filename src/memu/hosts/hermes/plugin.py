# memU managed Hermes plugin.
"""Bridge Hermes lifecycle events to memU's own Python environment."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

PYTHON = "__MEMU_PYTHON__"
BASE = "__MEMU_BASE_DIR__"
logger = logging.getLogger("memu.hermes")


def _call(action: str, event: dict[str, Any]) -> dict[str, Any]:
    from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

    result = subprocess.run(  # noqa: S603
        [PYTHON, "-m", "memu.hosts.hermes.hook", action, "--base-dir", BASE],
        input=json.dumps(event, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=25,
        env=dict(os.environ, HERMES_HOME=str(get_hermes_home()), PYTHONIOENCODING="utf-8"),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if result.returncode:
        raise RuntimeError("memU hook failed; check the host hook logs")  # noqa: TRY003
    output = json.loads(result.stdout)
    if not isinstance(output, dict):
        raise TypeError("Expected a memU hook response object")  # noqa: TRY003
    return output


def _retrieve(**event: Any) -> dict[str, Any] | None:
    try:
        if os.environ.get("MEMU_BRIDGING_RUN"):
            _call("remember-self", {"session_id": event.get("session_id")})
            return None
        if event.get("parent_session_id"):
            return None
        message = event.get("user_message")
        if isinstance(message, list):
            message = "\n".join(
                part["text"]
                for part in message
                if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
            )
        if not isinstance(message, str) or not message.strip():
            return None
        return _call("retrieve", {"prompt": message, "session_id": event.get("session_id")})
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
        logger.exception("memU retrieval failed")
        return None


def _memorize(**event: Any) -> None:
    if os.environ.get("MEMU_BRIDGING_RUN") or event.get("completed") is not True:
        return
    try:
        _call("memorize", {"session_id": event.get("session_id")})
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
        logger.exception("memU background memory launch failed")


def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", _retrieve)
    ctx.register_hook("on_session_end", _memorize)
