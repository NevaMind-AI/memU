# memU managed Hermes plugin.
"""Bridge Hermes lifecycle events to memU's own Python environment."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
from contextvars import copy_context
from typing import Any
from uuid import uuid4

PYTHON = "__MEMU_PYTHON__"
BASE = "__MEMU_BASE_DIR__"
logger = logging.getLogger("memu.hermes")
DELIVERY_PATTERN = re.compile(
    r"<!-- memu-hermes-retrieval:([0-9a-f]{32}) -->\n.*?\n<!-- /memu-hermes-retrieval:\1 -->", re.DOTALL
)


def _call(action: str, event: dict[str, Any]) -> dict[str, Any]:
    from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

    env = dict(os.environ, HERMES_HOME=str(get_hermes_home()), PYTHONIOENCODING="utf-8")
    # Hermes can export its own site-packages for a different Python version.
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    result = subprocess.run(  # noqa: S603
        [PYTHON, "-m", "memu.hosts.hermes.hook", action, "--base-dir", BASE],
        input=json.dumps({**event, "hermes_python": sys.executable, "hermes_sys_path": sys.path}, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=40,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip()[-4000:] or "No stderr output"
        raise RuntimeError(f"memU {action} exited {result.returncode}:\n{detail}")  # noqa: TRY003
    output = json.loads(result.stdout)
    if not isinstance(output, dict):
        raise TypeError("Expected a memU hook response object")  # noqa: TRY003
    return output


def register(ctx: Any) -> None:  # noqa: C901 -- Keep per-plugin state and lifecycle callbacks together.
    from hermes_cli.plugin_session import session_key  # type: ignore[import-not-found]

    lock = threading.Lock()
    requests: dict[str, dict[str, Any]] = {}
    deliveries: dict[str, str] = {}

    def memorize_if_settled(state: dict[str, Any]) -> None:
        with lock:
            sid = state["session_id"]
            if requests.get(sid) is not state or state["pending"] or not state["completed"]:
                return
            del requests[sid]
        try:
            _call("memorize", {"session_id": sid})
        except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
            logger.exception("memU background memory launch failed")

    def retrieve_in_background(state: dict[str, Any]) -> None:
        try:
            context = _call("retrieve", {"prompt": state["prompt"], "session_id": state["session_id"]}).get("context")
            with lock:
                if requests.get(state["session_id"]) is not state:
                    return
                if isinstance(context, str) and context:
                    deliveries[state["token"]] = state["session_id"]
                else:
                    state["pending"] = False
            if isinstance(context, str) and context:
                message = (
                    f"<!-- memu-hermes-retrieval:{state['token']} -->\n{context}\n"
                    f"<!-- /memu-hermes-retrieval:{state['token']} -->"
                )
                if not ctx.inject_message(message, session_key=state["route"]):
                    raise RuntimeError("Hermes rejected memU context injection; check the plugin injection grant")  # noqa: TRY003, TRY301
                logger.info("memU context queued for session %s", state["session_id"])
                return
        except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
            logger.exception("memU asynchronous retrieval failed")
            with lock:
                deliveries.pop(state["token"], None)
                state["pending"] = False
        memorize_if_settled(state)

    def retrieve(**event: Any) -> None:  # noqa: C901 -- Validate input, delivery identity and session routing.
        state = None
        try:
            sid = event.get("session_id")
            if os.environ.get("MEMU_BRIDGING_RUN"):
                _call("remember-self", {"session_id": sid})
                return
            if event.get("parent_session_id"):
                return
            message = event.get("user_message")
            if isinstance(message, list):
                message = "\n".join(
                    part["text"]
                    for part in message
                    if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
                )
            if not isinstance(sid, str) or not sid or not isinstance(message, str) or not message.strip():
                return
            consumed = False

            def remove_delivery(match: re.Match[str]) -> str:
                nonlocal consumed
                if deliveries.get(match[1]) != sid:
                    return match[0]
                del deliveries[match[1]]
                current = requests.get(sid)
                if current and current["token"] == match[1]:
                    current.update(pending=False, completed=False, turn_id=event.get("turn_id"))
                consumed = True
                return ""

            with lock:
                remaining = DELIVERY_PATTERN.sub(remove_delivery, message).strip()
            if consumed:
                message = remaining
                if not message:
                    return
            route = session_key()
            if not route:
                raise RuntimeError("Hermes did not bind a session_key for asynchronous retrieval")  # noqa: TRY003, TRY301
            state = {
                "session_id": sid,
                "route": route,
                "turn_id": event.get("turn_id"),
                "token": uuid4().hex,
                "prompt": message,
                "pending": True,
                "completed": False,
            }
            with lock:
                # A newer user input supersedes any unfinished retrieval for this route.
                for previous_sid, previous in list(requests.items()):
                    if previous["route"] == route:
                        del requests[previous_sid]
                requests[sid] = state
            logger.info("memU asynchronous retrieval starting for session %s", sid)
            threading.Thread(target=copy_context().run, args=(retrieve_in_background, state), daemon=True).start()
        except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
            logger.exception("memU retrieval launch failed")
            if state is not None:
                with lock:
                    state["pending"] = False

    def memorize(**event: Any) -> None:
        if os.environ.get("MEMU_BRIDGING_RUN") or event.get("completed") is not True:
            return
        sid = event.get("session_id")
        if not isinstance(sid, str):
            return
        with lock:
            state = requests.get(sid)
            if state is None or (state["turn_id"] and state["turn_id"] != event.get("turn_id")):
                return
            state["completed"] = True
        memorize_if_settled(state)

    def finalize(**event: Any) -> None:
        sid = event.get("session_id")
        if not isinstance(sid, str):
            return
        with lock:
            requests.pop(sid, None)
            for token, owner in list(deliveries.items()):
                if owner == sid:
                    del deliveries[token]

    ctx.register_hook("pre_llm_call", retrieve)
    ctx.register_hook("on_session_end", memorize)
    ctx.register_hook("on_session_finalize", finalize)
    logger.info("memU asynchronous hooks registered in process %s", os.getpid())
