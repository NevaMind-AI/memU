"""Tests for Tool Memory feature - specialized memory type for tracking tool usage."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for direct import - MUST be before any memu imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest  # noqa: E402

# Import directly from the models file path to avoid circular import through database/__init__.py
# We use importlib to import the module directly without triggering the package __init__
spec = importlib.util.spec_from_file_location("models", src_path / "memu" / "database" / "models.py")
assert spec is not None
assert spec.loader is not None
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

# Rebuild models to resolve forward references with proper namespace
rebuild_ns = {
    "Any": Any,
    "datetime": datetime,
    "MemoryType": models.MemoryType,
    "ToolCallResult": models.ToolCallResult,
}
models.ToolCallResult.model_rebuild(_types_namespace=rebuild_ns)
models.MemoryItem.model_rebuild(_types_namespace=rebuild_ns)

MemoryItem = models.MemoryItem
MemoryType = models.MemoryType
ToolCallResult = models.ToolCallResult

# Import tool memory utility functions
util_tool_spec = importlib.util.spec_from_file_location("util_tool", src_path / "memu" / "utils" / "tool.py")
assert util_tool_spec is not None
assert util_tool_spec.loader is not None
util_tool = importlib.util.module_from_spec(util_tool_spec)
util_tool_spec.loader.exec_module(util_tool)

add_tool_call = util_tool.add_tool_call
get_tool_statistics = util_tool.get_tool_statistics


class TestToolCallResult:
    """Tests for ToolCallResult model."""

    def test_create_tool_call_result(self):
        """Test creating a basic ToolCallResult."""
        result = ToolCallResult(
            tool_name="file_reader",
            input={"path": "/data/config.json"},
            output="File content here",
            success=True,
            time_cost=0.5,
            token_cost=100,
            score=0.95,
        )

        assert result.tool_name == "file_reader"
        assert result.input == {"path": "/data/config.json"}
        assert result.output == "File content here"
        assert result.success is True
        assert result.time_cost == 0.5
        assert result.token_cost == 100
        assert result.score == 0.95

    def test_generate_hash(self):
        """Test hash generation for deduplication."""
        result = ToolCallResult(
            tool_name="calculator",
            input={"a": 1, "b": 2},
            output="3",
        )

        hash1 = result.generate_hash()
        assert hash1 != ""
        assert len(hash1) == 32  # MD5 hex digest length

        # Same input/output should generate same hash
        result2 = ToolCallResult(
            tool_name="calculator",
            input={"a": 1, "b": 2},
            output="3",
        )
        assert result2.generate_hash() == hash1

        # Different input should generate different hash
        result3 = ToolCallResult(
            tool_name="calculator",
            input={"a": 2, "b": 3},
            output="5",
        )
        assert result3.generate_hash() != hash1

    def test_ensure_hash(self):
        """Test ensure_hash sets call_hash if empty."""
        result = ToolCallResult(
            tool_name="test_tool",
            input="test input",
            output="test output",
        )

        assert result.call_hash == ""
        result.ensure_hash()
        assert result.call_hash != ""
        assert len(result.call_hash) == 32

    def test_string_input(self):
        """Test ToolCallResult with string input."""
        result = ToolCallResult(
            tool_name="echo",
            input="hello world",
            output="hello world",
        )

        result.ensure_hash()
        assert result.call_hash != ""


class TestMemoryItemToolType:
    """Tests for MemoryItem with tool type."""

    def test_tool_memory_type_literal(self):
        """Test that 'tool' is a valid MemoryType."""
        from typing import get_args

        valid_types = get_args(MemoryType)
        assert "tool" in valid_types

    def test_create_tool_memory(self):
        """Test creating a tool type memory item with tool fields in extra."""
        item = MemoryItem(
            resource_id=None,
            memory_type="tool",
            summary="file_reader tool usage for config files",
            extra={
                "when_to_use": "When needing to read configuration files",
                "metadata": {"tool_name": "file_reader", "avg_success_rate": 0.95},
            },
        )

        assert item.memory_type == "tool"
        assert item.extra["when_to_use"] == "When needing to read configuration files"
        assert item.extra["metadata"]["tool_name"] == "file_reader"

    def test_add_tool_call(self):
        """Test adding tool call results to a tool memory."""
        item = MemoryItem(
            resource_id=None,
            memory_type="tool",
            summary="calculator tool usage",
        )

        tool_call = ToolCallResult(
            tool_name="calculator",
            input={"a": 1, "b": 2},
            output="3",
            success=True,
            time_cost=0.1,
            score=1.0,
        )

        add_tool_call(item, tool_call)

        tool_calls = item.extra.get("tool_calls", [])
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool_name"] == "calculator"
        assert tool_calls[0]["call_hash"] != ""  # ensure_hash was called

    def test_add_tool_call_wrong_type(self):
        """Test that add_tool_call fails for non-tool memories."""
        item = MemoryItem(
            resource_id=None,
            memory_type="profile",
            summary="User profile info",
        )

        tool_call = ToolCallResult(
            tool_name="test",
            input="test",
            output="test",
        )

        with pytest.raises(ValueError, match="can only be used with tool type memories"):
            add_tool_call(item, tool_call)

    def test_get_tool_statistics_empty(self):
        """Test statistics for memory with no tool calls."""
        item = MemoryItem(
            resource_id=None,
            memory_type="tool",
            summary="empty tool memory",
        )

        stats = get_tool_statistics(item)

        assert stats["total_calls"] == 0
        assert stats["recent_calls_analyzed"] == 0
        assert stats["avg_time_cost"] == 0.0
        assert stats["success_rate"] == 0.0
        assert stats["avg_score"] == 0.0
        assert stats["avg_token_cost"] == 0.0

    def test_get_tool_statistics(self):
        """Test statistics calculation for tool calls."""
        # Tool calls are stored as dicts in extra
        item = MemoryItem(
            resource_id=None,
            memory_type="tool",
            summary="calculator tool",
            extra={
                "tool_calls": [
                    {
                        "tool_name": "calc",
                        "input": "1+1",
                        "output": "2",
                        "success": True,
                        "time_cost": 0.1,
                        "score": 1.0,
                        "token_cost": 10,
                    },
                    {
                        "tool_name": "calc",
                        "input": "2+2",
                        "output": "4",
                        "success": True,
                        "time_cost": 0.2,
                        "score": 0.9,
                        "token_cost": 15,
                    },
                    {
                        "tool_name": "calc",
                        "input": "bad",
                        "output": "error",
                        "success": False,
                        "time_cost": 0.5,
                        "score": 0.0,
                        "token_cost": 5,
                    },
                ]
            },
        )

        stats = get_tool_statistics(item)

        assert stats["total_calls"] == 3
        assert stats["recent_calls_analyzed"] == 3
        assert stats["success_rate"] == pytest.approx(0.6667, rel=0.01)  # 2/3
        assert stats["avg_time_cost"] == pytest.approx(0.267, rel=0.01)  # (0.1+0.2+0.5)/3
        assert stats["avg_score"] == pytest.approx(0.633, rel=0.01)  # (1.0+0.9+0.0)/3
        assert stats["avg_token_cost"] == pytest.approx(10.0, rel=0.01)  # (10+15+5)/3

    def test_get_tool_statistics_recent_n(self):
        """Test statistics with recent_n limit."""
        item = MemoryItem(
            resource_id=None,
            memory_type="tool",
            summary="tool with many calls",
            extra={
                "tool_calls": [
                    {"tool_name": "t", "input": "1", "output": "1", "success": False, "time_cost": 1.0, "score": 0.0},
                    {"tool_name": "t", "input": "2", "output": "2", "success": True, "time_cost": 0.1, "score": 1.0},
                    {"tool_name": "t", "input": "3", "output": "3", "success": True, "time_cost": 0.1, "score": 1.0},
                ]
            },
        )

        # Only analyze last 2 calls
        stats = get_tool_statistics(item, recent_n=2)

        assert stats["total_calls"] == 3
        assert stats["recent_calls_analyzed"] == 2
        assert stats["success_rate"] == 1.0  # Both recent calls succeeded


class TestMemoryItemNewFields:
    """Tests for tool-related fields stored in extra."""

    def test_when_to_use_field(self):
        """Test when_to_use field stored in extra for retrieval hints."""
        item = MemoryItem(
            resource_id=None,
            memory_type="profile",
            summary="User prefers dark mode",
            extra={"when_to_use": "When configuring UI settings or themes"},
        )

        assert item.extra["when_to_use"] == "When configuring UI settings or themes"

    def test_metadata_field(self):
        """Test metadata field stored in extra for type-specific data."""
        item = MemoryItem(
            resource_id=None,
            memory_type="event",
            summary="User attended conference",
            extra={
                "metadata": {
                    "event_date": "2026-01-15",
                    "location": "San Francisco",
                    "attendees": ["Alice", "Bob"],
                }
            },
        )

        assert item.extra.get("metadata") is not None
        assert item.extra["metadata"]["event_date"] == "2026-01-15"
        assert item.extra["metadata"]["location"] == "San Francisco"
        assert len(item.extra["metadata"]["attendees"]) == 2

    def test_default_values(self):
        """Test that extra defaults to empty dict."""
        item = MemoryItem(
            resource_id=None,
            memory_type="knowledge",
            summary="Python is a programming language",
        )

        assert item.extra.get("when_to_use") is None
        assert item.extra.get("metadata") is None
        assert item.extra.get("tool_calls") is None
