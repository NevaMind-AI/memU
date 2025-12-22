from __future__ import annotations

import copy
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from memu.workflow.step import WorkflowStep


@dataclass
class PipelineRevision:
    name: str
    revision: int
    steps: list[WorkflowStep]
    created_at: float
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineManager:
    def __init__(self, *, available_capabilities: set[str] | None = None, llm_profiles: set[str] | None = None):
        self.available_capabilities = available_capabilities or set()
        self.llm_profiles = llm_profiles or {"default"}
        self._pipelines: dict[str, list[PipelineRevision]] = {}

    def register(
        self,
        name: str,
        steps: Iterable[WorkflowStep],
        *,
        initial_state_keys: set[str] | None = None,
    ) -> None:
        steps_list = list(steps)
        meta = {"initial_state_keys": set(initial_state_keys or set())}
        self._validate_steps(steps_list, initial_state_keys=meta["initial_state_keys"])
        self._pipelines[name] = [
            PipelineRevision(
                name=name,
                revision=1,
                steps=steps_list,
                created_at=time.time(),
                metadata=meta,
            )
        ]

    def build(self, name: str) -> list[WorkflowStep]:
        revision = self._current_revision(name)
        return [step.copy() for step in revision.steps]

    def config_step(self, name: str, step_id: str, configs: dict[str, Any]) -> int:
        def mutator(steps: list[WorkflowStep]) -> None:
            for step in steps:
                if step.step_id == step_id:
                    merged = dict(getattr(step, "config", {}) or {})
                    merged.update(configs)
                    step.config = merged
                    return
            msg = f"Step '{step_id}' not found in pipeline '{name}'"
            raise KeyError(msg)

        return self._mutate(name, mutator)

    def insert_after(self, name: str, target_step_id: str, new_step: WorkflowStep) -> int:
        def mutator(steps: list[WorkflowStep]) -> None:
            for idx, step in enumerate(steps):
                if step.step_id == target_step_id:
                    steps.insert(idx + 1, new_step)
                    return
            msg = f"Step '{target_step_id}' not found in pipeline '{name}'"
            raise KeyError(msg)

        return self._mutate(name, mutator)

    def insert_before(self, name: str, target_step_id: str, new_step: WorkflowStep) -> int:
        def mutator(steps: list[WorkflowStep]) -> None:
            for idx, step in enumerate(steps):
                if step.step_id == target_step_id:
                    steps.insert(idx, new_step)
                    return
            msg = f"Step '{target_step_id}' not found in pipeline '{name}'"
            raise KeyError(msg)

        return self._mutate(name, mutator)

    def replace_step(self, name: str, target_step_id: str, new_step: WorkflowStep) -> int:
        def mutator(steps: list[WorkflowStep]) -> None:
            for idx, step in enumerate(steps):
                if step.step_id == target_step_id:
                    steps[idx] = new_step
                    return
            msg = f"Step '{target_step_id}' not found in pipeline '{name}'"
            raise KeyError(msg)

        return self._mutate(name, mutator)

    def remove_step(self, name: str, target_step_id: str) -> int:
        def mutator(steps: list[WorkflowStep]) -> None:
            for idx, step in enumerate(steps):
                if step.step_id == target_step_id:
                    steps.pop(idx)
                    return
            msg = f"Step '{target_step_id}' not found in pipeline '{name}'"
            raise KeyError(msg)

        return self._mutate(name, mutator)

    def _mutate(self, name: str, mutator: Any) -> int:
        revision = self._current_revision(name)
        steps = [step.copy() for step in revision.steps]
        metadata = copy.deepcopy(revision.metadata)
        mutator(steps)
        self._validate_steps(steps, initial_state_keys=metadata.get("initial_state_keys"))
        new_revision = PipelineRevision(
            name=name,
            revision=revision.revision + 1,
            steps=steps,
            created_at=time.time(),
            metadata=metadata,
        )
        self._pipelines[name].append(new_revision)
        return new_revision.revision

    def _current_revision(self, name: str) -> PipelineRevision:
        revisions = self._pipelines.get(name)
        if not revisions:
            msg = f"Pipeline '{name}' not registered"
            raise KeyError(msg)
        return revisions[-1]

    def _validate_steps(self, steps: list[WorkflowStep], *, initial_state_keys: set[str] | None) -> None:
        seen: set[str] = set()
        available_keys = set(initial_state_keys or set())

        for step in steps:
            if step.step_id in seen:
                msg = f"Duplicate step_id '{step.step_id}' found"
                raise ValueError(msg)
            seen.add(step.step_id)

            if self.available_capabilities:
                unknown_caps = step.capabilities - self.available_capabilities
                if unknown_caps:
                    msg = f"Step '{step.step_id}' requests unavailable capabilities: {', '.join(sorted(unknown_caps))}"
                    raise ValueError(msg)

            if getattr(step, "config", None):
                profile_name = step.config.get("llm_profile")
                if profile_name and profile_name not in self.llm_profiles:
                    msg = (
                        f"Step '{step.step_id}' references unknown llm_profile '{profile_name}'. "
                        f"Available profiles: {', '.join(sorted(self.llm_profiles))}"
                    )
                    raise ValueError(msg)

            missing = step.requires - available_keys
            if missing:
                msg = (
                    f"Step '{step.step_id}' requires missing state keys: {', '.join(sorted(missing))}. "
                    "Ensure previous steps produce them or initial_state_keys contains them."
                )
                raise ValueError(msg)

            available_keys.update(step.produces)

    def revision_token(self) -> str:
        parts: list[str] = []
        for name, revisions in sorted(self._pipelines.items()):
            parts.append(f"{name}:v{revisions[-1].revision}")
        return "|".join(parts)
