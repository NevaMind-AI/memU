from __future__ import annotations

import ast
from pathlib import Path

from memu.workflow.pipeline import PipelineManager
from memu.workflow.step import WorkflowStep

ROOT = Path(__file__).resolve().parents[1]


def _noop_step(state: dict[str, object], context: object) -> dict[str, object]:
    return state


def test_pipeline_manager_validates_all_llm_profile_config_keys() -> None:
    manager = PipelineManager(available_capabilities={"llm"}, llm_profiles={"default"})

    for profile_key in ("llm_profile", "chat_llm_profile", "embed_llm_profile"):
        try:
            manager.register(
                f"pipeline_{profile_key}",
                [
                    WorkflowStep(
                        step_id="step",
                        role="test",
                        handler=_noop_step,
                        capabilities={"llm"},
                        config={profile_key: "missing"},
                    )
                ],
            )
        except ValueError as exc:
            assert f"unknown {profile_key} 'missing'" in str(exc)
        else:
            raise AssertionError(f"PipelineManager should reject unknown {profile_key}")


def test_pipeline_manager_rejects_blank_and_non_string_llm_profile_references() -> None:
    manager = PipelineManager(available_capabilities={"llm"}, llm_profiles={"default"})

    for value in ("", " ", 123):
        try:
            manager.register(
                f"pipeline_{value!r}",
                [
                    WorkflowStep(
                        step_id="step",
                        role="test",
                        handler=_noop_step,
                        capabilities={"llm"},
                        config={"chat_llm_profile": value},
                    )
                ],
            )
        except ValueError as exc:
            assert "profile name must be non-empty" in str(exc)
        else:
            raise AssertionError("PipelineManager should reject invalid profile references")


def test_pipeline_manager_revalidates_profile_references_on_config_mutation() -> None:
    manager = PipelineManager(available_capabilities={"llm"}, llm_profiles={"default"})
    manager.register(
        "pipeline",
        [
            WorkflowStep(
                step_id="step",
                role="test",
                handler=_noop_step,
                capabilities={"llm"},
                config={"chat_llm_profile": "default"},
            )
        ],
    )

    try:
        manager.config_step("pipeline", "step", {"chat_llm_profile": " "})
    except ValueError as exc:
        assert "profile name must be non-empty" in str(exc)
    else:
        raise AssertionError("PipelineManager should reject invalid profile references during mutation")


def test_llm_retrieve_route_intention_step_declares_route_intention_dependency() -> None:
    source = (ROOT / "src/memu/app/retrieve.py").read_text(encoding="utf-8")
    workflow_source = _function_source(source, "_build_llm_retrieve_workflow")
    route_step_source = workflow_source.split('step_id="route_category"', 1)[0]

    assert 'requires={"route_intention", "original_query", "context_queries", "skip_rewrite"}' in route_step_source


def _function_source(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"function {name!r} not found")
