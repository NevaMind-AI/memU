from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

WorkflowState = dict[str, Any]
WorkflowContext = Mapping[str, Any] | None
WorkflowHandler = Callable[[WorkflowState, WorkflowContext], Awaitable[WorkflowState] | WorkflowState]


@dataclass
class WorkflowStep:
    step_id: str
    role: str
    handler: WorkflowHandler
    description: str = ""
    requires: set[str] = field(default_factory=set)
    produces: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)
    config: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> WorkflowStep:
        """Create a shallow copy with copied mutable fields but shared handler."""
        return WorkflowStep(
            step_id=self.step_id,
            role=self.role,
            handler=self.handler,  # Keep reference, don't copy
            description=self.description,
            requires=set(self.requires),
            produces=set(self.produces),
            capabilities=set(self.capabilities),
            config=dict(self.config),
        )

    async def run(self, state: WorkflowState, context: WorkflowContext) -> WorkflowState:
        result = self.handler(state, context)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, Mapping):
            msg = f"Workflow step '{self.step_id}' must return a mapping, got {type(result).__name__}"
            raise TypeError(msg)
        return dict(result)


async def run_steps(
    name: str,
    steps: list[WorkflowStep],
    initial_state: WorkflowState,
    context: WorkflowContext = None,
) -> WorkflowState:
    state = dict(initial_state)
    for step in steps:
        missing = step.requires - state.keys()
        if missing:
            msg = f"Workflow '{name}' missing required keys for step '{step.step_id}': {', '.join(sorted(missing))}"
            raise KeyError(msg)
        step_context: dict[str, Any] = dict(context) if context else {}
        step_context["step_id"] = step.step_id
        if step.config:
            step_context["step_config"] = step.config
        state = await step.run(state, step_context)
    return state
