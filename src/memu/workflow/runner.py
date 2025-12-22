from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from memu.workflow.step import WorkflowContext, WorkflowState, WorkflowStep, run_steps


@runtime_checkable
class WorkflowRunner(Protocol):
    """Interface for executing workflows via different backends."""

    name: str

    async def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        initial_state: WorkflowState,
        context: WorkflowContext = None,
    ) -> WorkflowState: ...


class LocalWorkflowRunner:
    name = "local"

    async def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        initial_state: WorkflowState,
        context: WorkflowContext = None,
    ) -> WorkflowState:
        return await run_steps(workflow_name, steps, initial_state, context)


RunnerFactory = Callable[[], WorkflowRunner]
WorkflowRunnerSpec = WorkflowRunner | str | None


_RUNNER_FACTORIES: dict[str, RunnerFactory] = {
    "local": LocalWorkflowRunner,
    "sync": LocalWorkflowRunner,
}


def register_workflow_runner(name: str, factory: RunnerFactory) -> None:
    """Register a workflow runner factory (e.g., temporal, burr)."""
    key = name.strip().lower()
    if not key:
        msg = "Workflow runner name must be non-empty"
        raise ValueError(msg)
    _RUNNER_FACTORIES[key] = factory


def resolve_workflow_runner(spec: WorkflowRunnerSpec) -> WorkflowRunner:
    """
    Resolve a workflow runner from a name, instance, or None (defaults to local).

    External backends (Temporal, Burr, etc.) can be exposed by registering a factory
    with `register_workflow_runner` and passing the runner name here.
    """
    if isinstance(spec, WorkflowRunner):
        return spec

    runner_name = (spec or "local").strip().lower()
    factory = _RUNNER_FACTORIES.get(runner_name)
    if factory is None:
        msg = f"Unknown workflow runner '{runner_name}'. Register it with register_workflow_runner before use."
        raise ValueError(msg)

    runner = factory()
    if not isinstance(runner, WorkflowRunner):
        msg = f"Factory for runner '{runner_name}' must return a WorkflowRunner"
        raise TypeError(msg)
    return runner
