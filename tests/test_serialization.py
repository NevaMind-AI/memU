from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from memu.llm.wrapper import _extract_usage_from_raw_response
from memu.utils.serialization import model_dump_without_embeddings

ROOT = Path(__file__).resolve().parents[1]


class ResponseRecord(BaseModel):
    id: str
    summary: str
    embedding: list[float] | None
    created_at: datetime
    extra: dict[str, object] = Field(default_factory=dict)


class CompletionTokenDetails(BaseModel):
    reasoning_tokens: int
    generated_at: datetime


class PromptTokenDetails(BaseModel):
    cached_tokens: int


class UsageRecord(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    completion_tokens_details: CompletionTokenDetails
    prompt_tokens_details: PromptTokenDetails


class RawLLMResponse:
    def __init__(self, usage: object) -> None:
        self.choices = [{"finish_reason": "stop"}]
        self.usage = usage


class LegacyCompletionTokenDetails:
    reasoning_tokens = 2

    def model_dump(self) -> dict[str, object]:
        return {
            "reasoning_tokens": self.reasoning_tokens,
            "generated_at": datetime(2026, 6, 5, 3, 0, tzinfo=timezone.utc),
        }


class LegacyUsageRecord:
    prompt_tokens = 8
    completion_tokens = 2
    total_tokens = 10
    completion_tokens_details = LegacyCompletionTokenDetails()
    prompt_tokens_details = {"cached_tokens": 4}


def test_model_dump_without_embeddings_returns_json_safe_values() -> None:
    record = ResponseRecord(
        id="m1",
        summary="User likes concise answers.",
        embedding=[0.1, 0.2, 0.3],
        created_at=datetime(2026, 6, 5, 1, 40, tzinfo=timezone.utc),
        extra={"score": 0.9},
    )

    data = model_dump_without_embeddings(record)

    assert data == {
        "id": "m1",
        "summary": "User likes concise answers.",
        "created_at": "2026-06-05T01:40:00Z",
        "extra": {"score": 0.9},
    }


def test_memorize_response_relations_use_json_safe_public_dump() -> None:
    source = (ROOT / "src/memu/app/memorize.py").read_text(encoding="utf-8")
    function_source = _function_source(source, "_memorize_build_response")

    assert "relations = [self._model_dump_without_embeddings(rel)" in function_source
    assert "rel.model_dump()" not in function_source


def test_tool_call_history_uses_json_safe_model_dump() -> None:
    source = (ROOT / "src/memu/utils/tool.py").read_text(encoding="utf-8")
    function_source = _function_source(source, "add_tool_call")

    assert 'tool_call.model_dump(mode="json")' in function_source
    assert "tool_call.model_dump())" not in function_source


def test_llm_usage_breakdown_is_json_safe() -> None:
    raw_response = RawLLMResponse(
        UsageRecord(
            prompt_tokens=10,
            completion_tokens=4,
            total_tokens=14,
            completion_tokens_details=CompletionTokenDetails(
                reasoning_tokens=3,
                generated_at=datetime(2026, 6, 5, 2, 30, tzinfo=timezone.utc),
            ),
            prompt_tokens_details=PromptTokenDetails(cached_tokens=6),
        )
    )

    usage = _extract_usage_from_raw_response(kind="chat", raw_response=raw_response)

    assert usage["finish_reason"] == "stop"
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 4
    assert usage["total_tokens"] == 14
    assert usage["cached_input_tokens"] == 6
    assert usage["reasoning_tokens"] == 3
    assert usage["tokens_breakdown"] == {
        "reasoning_tokens": 3,
        "generated_at": "2026-06-05T02:30:00Z",
    }
    json.dumps(usage)


def test_llm_usage_breakdown_accepts_legacy_model_dump_signature() -> None:
    raw_response = RawLLMResponse(LegacyUsageRecord())

    usage = _extract_usage_from_raw_response(kind="chat", raw_response=raw_response)

    assert usage["cached_input_tokens"] == 4
    assert usage["tokens_breakdown"] == {
        "reasoning_tokens": 2,
        "generated_at": "2026-06-05T03:00:00+00:00",
    }
    json.dumps(usage)


def test_llm_usage_extraction_accepts_responses_style_token_names() -> None:
    raw_response = {
        "choices": [{"finish_reason": "length"}],
        "usage": {
            "input_tokens": 11,
            "output_tokens": 7,
            "total_tokens": 18,
            "input_tokens_details": {"cached_tokens": 5},
            "output_tokens_details": {
                "reasoning_tokens": 2,
                "accepted_prediction_tokens": 1,
            },
        },
    }

    usage = _extract_usage_from_raw_response(kind="chat", raw_response=raw_response)

    assert usage["finish_reason"] == "length"
    assert usage["input_tokens"] == 11
    assert usage["output_tokens"] == 7
    assert usage["total_tokens"] == 18
    assert usage["cached_input_tokens"] == 5
    assert usage["reasoning_tokens"] == 2
    assert usage["tokens_breakdown"] == {
        "reasoning_tokens": 2,
        "accepted_prediction_tokens": 1,
    }
    json.dumps(usage)


def test_memory_item_extra_defaults_are_per_record_factories() -> None:
    checked = [
        ("src/memu/database/models.py", "MemoryItem"),
        ("src/memu/database/sqlite/models.py", "SQLiteMemoryItemModel"),
        ("src/memu/database/postgres/models.py", "MemoryItemModel"),
    ]

    for relative_path, class_name in checked:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assignment = _class_assignment(source, class_name, "extra")

        assert isinstance(assignment, ast.Call), f"{relative_path}:{class_name}.extra must call Field"
        assert getattr(assignment.func, "id", "") == "Field"
        assert any(
            keyword.arg == "default_factory"
            and getattr(keyword.value, "id", None) == "dict"
            for keyword in assignment.keywords
        ), f"{relative_path}:{class_name}.extra must use Field(default_factory=dict)"


def _function_source(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"function {name!r} not found")


def _class_assignment(source: str, class_name: str, field_name: str) -> ast.expr:
    module = ast.parse(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if isinstance(statement.target, ast.Name) and statement.target.id == field_name:
                assert statement.value is not None
                return statement.value
    raise AssertionError(f"{class_name}.{field_name} assignment not found")
