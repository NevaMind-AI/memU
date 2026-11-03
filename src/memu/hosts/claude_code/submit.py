"""Classify automatic Submit messages before starting memory work."""

from typing import Any


def is_automatic(event: dict[str, Any]) -> bool:
    """Desktop submits hook feedback as task notifications, firing Submit again."""
    origin = event.get("origin")
    prompt = event.get("prompt")
    return (isinstance(origin, dict) and origin.get("kind") == "task-notification") or (
        isinstance(prompt, str) and prompt.lstrip().startswith("<task-notification>")
    )
