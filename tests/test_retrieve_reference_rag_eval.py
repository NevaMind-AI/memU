from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tests.test_retrieve_reference_rag import _build_service, _seed_category, _seed_item


@dataclass(frozen=True)
class _EvalMetrics:
    cited_item_recall: float
    precision_at_k: float
    duplicate_count: int
    scope_leak_count: int
    missing_ref_error_count: int


def _returned_ref_ids(result: dict[str, Any]) -> list[str]:
    ref_ids: list[str] = []
    for item in result["items"]:
        ref_id = (item.get("extra") or {}).get("ref_id")
        if isinstance(ref_id, str):
            ref_ids.append(ref_id)
    return ref_ids


def _count_duplicates(values: list[str]) -> int:
    return len(values) - len(set(values))


async def _run_synthetic_eval_case(
    *,
    use_category_references: bool,
    case_id: int,
) -> tuple[dict[str, Any], set[str], int]:
    service = _build_service(use_category_references=use_category_references, top_k=2)
    expected_refs = {f"case-{case_id}-primary", f"case-{case_id}-secondary"}

    _seed_item(
        service,
        summary=f"Case {case_id} cited primary remediation",
        user_id="eval-user",
        embedding=[0.0, 1.0, 0.0],
        ref_id=f"case-{case_id}-primary",
    )
    _seed_item(
        service,
        summary=f"Case {case_id} cited secondary remediation",
        user_id="eval-user",
        embedding=[0.0, 1.0, 0.0],
        ref_id=f"case-{case_id}-secondary",
    )
    _seed_item(
        service,
        summary=f"Case {case_id} vector distractor one",
        user_id="eval-user",
        embedding=[1.0, 0.0, 0.0],
    )
    _seed_item(
        service,
        summary=f"Case {case_id} vector distractor two",
        user_id="eval-user",
        embedding=[1.0, 0.0, 0.0],
    )
    _seed_item(
        service,
        summary=f"Case {case_id} out-of-scope cited remediation",
        user_id="other-user",
        embedding=[1.0, 0.0, 0.0],
        ref_id=f"case-{case_id}-primary",
    )
    _seed_category(
        service,
        user_id="eval-user",
        summary=(
            f"The exact remediation was recorded in two cited items "
            f"[ref:case-{case_id}-primary,case-{case_id}-secondary]. "
            f"The summary also contains a stale citation [ref:case-{case_id}-missing]."
        ),
    )

    missing_ref_errors = 0
    try:
        result = await service.retrieve(
            queries=[{"role": "user", "content": {"text": f"Which case {case_id} remediation applies?"}}],
            where={"user_id": "eval-user"},
        )
    except Exception:
        missing_ref_errors = 1
        result = {"items": []}

    return result, expected_refs, missing_ref_errors


async def _run_synthetic_eval(*, use_category_references: bool, case_count: int = 3) -> _EvalMetrics:
    returned_expected = 0
    expected_total = 0
    returned_total = 0
    duplicate_count = 0
    scope_leak_count = 0
    missing_ref_error_count = 0

    for case_id in range(case_count):
        result, expected_refs, missing_ref_errors = await _run_synthetic_eval_case(
            use_category_references=use_category_references,
            case_id=case_id,
        )
        returned_refs = _returned_ref_ids(result)
        returned_expected += len(set(returned_refs) & expected_refs)
        expected_total += len(expected_refs)
        returned_total += len(result["items"])
        duplicate_count += _count_duplicates([item["id"] for item in result["items"]])
        scope_leak_count += sum(1 for item in result["items"] if item.get("user_id") != "eval-user")
        missing_ref_error_count += missing_ref_errors

    return _EvalMetrics(
        cited_item_recall=returned_expected / expected_total,
        precision_at_k=returned_expected / returned_total if returned_total else 0.0,
        duplicate_count=duplicate_count,
        scope_leak_count=scope_leak_count,
        missing_ref_error_count=missing_ref_error_count,
    )


async def test_synthetic_reference_aware_rag_improves_cited_item_recall_without_leaks() -> None:
    vector_only = await _run_synthetic_eval(use_category_references=False)
    reference_aware = await _run_synthetic_eval(use_category_references=True)

    assert vector_only == _EvalMetrics(
        cited_item_recall=0.0,
        precision_at_k=0.0,
        duplicate_count=0,
        scope_leak_count=0,
        missing_ref_error_count=0,
    )
    assert reference_aware == _EvalMetrics(
        cited_item_recall=1.0,
        precision_at_k=1.0,
        duplicate_count=0,
        scope_leak_count=0,
        missing_ref_error_count=0,
    )


async def test_langgraph_search_tool_uses_reference_aware_retrieve_when_available() -> None:
    pytest.importorskip("langgraph")
    from memu.integrations.langgraph import MemULangGraphTools

    service = _build_service(use_category_references=True, top_k=1)
    _seed_item(
        service,
        summary="LangGraph tool should surface this cited deployment memory",
        user_id="agent-user",
        embedding=[0.0, 1.0, 0.0],
        ref_id="langgraph-cited-ref",
    )
    _seed_item(
        service,
        summary="LangGraph vector distractor",
        user_id="agent-user",
        embedding=[1.0, 0.0, 0.0],
    )
    _seed_category(
        service,
        user_id="agent-user",
        summary="The agent should follow the cited memory [ref:langgraph-cited-ref].",
    )
    search_tool = MemULangGraphTools(service).search_memory_tool()

    result = await search_tool.ainvoke({"query": "Which deployment memory matters?", "user_id": "agent-user"})

    assert "LangGraph tool should surface this cited deployment memory" in result
    assert "LangGraph vector distractor" not in result
