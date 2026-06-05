from __future__ import annotations

INSTALL_HINT = (
    "The proactive Claude example requires claude-agent-sdk. "
    "Install the optional extra with `pip install 'memu-py[claude]'`, "
    "or run `uv sync --extra claude` from a source checkout."
)

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
        tool,
    )
except ModuleNotFoundError as exc:
    if exc.name != "claude_agent_sdk":
        raise
    raise SystemExit(INSTALL_HINT) from exc

__all__ = [
    "AssistantMessage",
    "ClaudeAgentOptions",
    "ClaudeSDKClient",
    "ResultMessage",
    "TextBlock",
    "create_sdk_mcp_server",
    "tool",
]
