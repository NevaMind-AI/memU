"""Utility functions for tool memory operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.database.models import MemoryItem, ToolCallResult


def get_tool_calls(item: MemoryItem) -> list[dict[str, Any]]:
    """Get tool calls from a memory item's extra field.

    Args:
        item: The MemoryItem to get tool calls from

    Returns:
        List of tool call dicts, or empty list if none exist
    """
    result: list[dict[str, Any]] = (item.extra or {}).get("tool_calls", [])
    return result


def set_tool_calls(item: MemoryItem, tool_calls: list[dict[str, Any]]) -> None:
    """Set tool calls in a memory item's extra field.

    Args:
        item: The MemoryItem to set tool calls on
        tool_calls: The list of tool call dicts to set
    """
    if item.extra is None:
        item.extra = {}
    item.extra["tool_calls"] = tool_calls


def add_tool_call(item: MemoryItem, tool_call: ToolCallResult) -> None:
    """Add a tool call result to a memory item (for tool type memories).

    Args:
        item: The MemoryItem to add the tool call to (must be tool type)
        tool_call: The ToolCallResult to add

    Raises:
        ValueError: If the memory item is not of type 'tool'
    """
    if item.memory_type != "tool":
        msg = "add_tool_call can only be used with tool type memories"
        raise ValueError(msg)
    tool_call.ensure_hash()
    tool_calls = get_tool_calls(item)
    tool_calls.append(tool_call.model_dump())
    set_tool_calls(item, tool_calls)


def get_tool_statistics(item: MemoryItem, recent_n: int = 20) -> dict[str, Any]:
    """Calculate statistics for the most recent N tool calls.

    Args:
        item: The MemoryItem to calculate statistics for
        recent_n: Number of recent calls to analyze (default: 20)

    Returns:
        Dictionary with total_calls, recent_calls_analyzed, avg_time_cost,
        success_rate, avg_score, avg_token_cost
    """
    tool_calls = get_tool_calls(item)
    if not tool_calls:
        return {
            "total_calls": 0,
            "recent_calls_analyzed": 0,
            "avg_time_cost": 0.0,
            "success_rate": 0.0,
            "avg_score": 0.0,
            "avg_token_cost": 0.0,
        }

    recent_calls = tool_calls[-recent_n:]
    recent_count = len(recent_calls)

    # Calculate statistics (tool_calls are now dicts, not ToolCallResult objects)
    total_time = sum(c.get("time_cost", 0.0) for c in recent_calls)
    avg_time_cost = total_time / recent_count if recent_count > 0 else 0.0

    successful = sum(1 for c in recent_calls if c.get("success", True))
    success_rate = successful / recent_count if recent_count > 0 else 0.0

    total_score = sum(c.get("score", 0.0) for c in recent_calls)
    avg_score = total_score / recent_count if recent_count > 0 else 0.0

    valid_token_calls = [c for c in recent_calls if c.get("token_cost", -1) >= 0]
    avg_token_cost = (
        sum(c.get("token_cost", 0) for c in valid_token_calls) / len(valid_token_calls) if valid_token_calls else 0.0
    )

    return {
        "total_calls": len(tool_calls),
        "recent_calls_analyzed": recent_count,
        "avg_time_cost": round(avg_time_cost, 3),
        "success_rate": round(success_rate, 4),
        "avg_score": round(avg_score, 3),
        "avg_token_cost": round(avg_token_cost, 2),
    }
