from __future__ import annotations

import inspect
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memu.workflow.step import WorkflowState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowStepContext:
    """Context information for a workflow step execution."""

    workflow_name: str
    step_id: str
    step_role: str
    step_context: dict[str, Any]


@dataclass(frozen=True)
class _WorkflowInterceptor:
    interceptor_id: int
    fn: Callable[..., Any]
    name: str | None


@dataclass(frozen=True)
class _WorkflowInterceptorSnapshot:
    before: tuple[_WorkflowInterceptor, ...]
    after: tuple[_WorkflowInterceptor, ...]
    on_error: tuple[_WorkflowInterceptor, ...]


class WorkflowInterceptorHandle:
    """Handle for disposing a registered workflow interceptor."""

    def __init__(self, registry: WorkflowInterceptorRegistry, interceptor_id: int) -> None:
        self._registry = registry
        self._interceptor_id = interceptor_id
        self._disposed = False

    def dispose(self) -> bool:
        """Remove the interceptor from the registry. Returns True if removed."""
        if self._disposed:
            return False
        self._disposed = True
        return self._registry.remove(self._interceptor_id)


class WorkflowInterceptorRegistry:
    """
    Registry for workflow step interceptors.

    Interceptors are called before and after each workflow step execution.
    Unlike LLM interceptors, workflow interceptors do not support filtering,
    priority, or ordering - they are called in registration order.
    """

    def __init__(self, *, strict: bool = False) -> None:
        self._before: tuple[_WorkflowInterceptor, ...] = ()
        self._after: tuple[_WorkflowInterceptor, ...] = ()
        self._on_error: tuple[_WorkflowInterceptor, ...] = ()
        self._lock = threading.Lock()
        self._seq = 0
        self._strict = strict

    @property
    def strict(self) -> bool:
        """If True, interceptor exceptions will propagate instead of being logged."""
        return self._strict

    def register_before(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        Register an interceptor to be called before each step.

        The interceptor receives (step_context: WorkflowStepContext, state: WorkflowState).
        """
        return self._register("before", fn, name=name)

    def register_after(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        Register an interceptor to be called after each step.

        The interceptor receives (step_context: WorkflowStepContext, state: WorkflowState).
        """
        return self._register("after", fn, name=name)

    def register_on_error(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        Register an interceptor to be called when a step raises an exception.

        The interceptor receives (step_context: WorkflowStepContext, state: WorkflowState, error: Exception).
        """
        return self._register("on_error", fn, name=name)

    def _register(
        self,
        kind: str,
        fn: Callable[..., Any],
        *,
        name: str | None,
    ) -> WorkflowInterceptorHandle:
        if not callable(fn):
            msg = "Interceptor must be callable"
            raise TypeError(msg)
        with self._lock:
            self._seq += 1
            interceptor = _WorkflowInterceptor(
                interceptor_id=self._seq,
                fn=fn,
                name=name,
            )
            if kind == "before":
                self._before = (*self._before, interceptor)
            elif kind == "after":
                self._after = (*self._after, interceptor)
            elif kind == "on_error":
                self._on_error = (*self._on_error, interceptor)
            else:
                msg = f"Unknown interceptor kind '{kind}'"
                raise ValueError(msg)
        return WorkflowInterceptorHandle(self, interceptor.interceptor_id)

    def remove(self, interceptor_id: int) -> bool:
        """Remove an interceptor by ID. Returns True if found and removed."""
        with self._lock:
            removed = False
            before = tuple(i for i in self._before if i.interceptor_id != interceptor_id)
            after = tuple(i for i in self._after if i.interceptor_id != interceptor_id)
            on_error = tuple(i for i in self._on_error if i.interceptor_id != interceptor_id)
            if len(before) != len(self._before):
                removed = True
                self._before = before
            if len(after) != len(self._after):
                removed = True
                self._after = after
            if len(on_error) != len(self._on_error):
                removed = True
                self._on_error = on_error
        return removed

    def snapshot(self) -> _WorkflowInterceptorSnapshot:
        """Get a point-in-time snapshot of registered interceptors."""
        return _WorkflowInterceptorSnapshot(self._before, self._after, self._on_error)


async def run_before_interceptors(
    interceptors: tuple[_WorkflowInterceptor, ...],
    step_context: WorkflowStepContext,
    state: WorkflowState,
    *,
    strict: bool = False,
) -> None:
    """Run all before-step interceptors."""
    for interceptor in interceptors:
        await _safe_invoke_interceptor(interceptor, strict, step_context, state)


async def run_after_interceptors(
    interceptors: tuple[_WorkflowInterceptor, ...],
    step_context: WorkflowStepContext,
    state: WorkflowState,
    *,
    strict: bool = False,
) -> None:
    """Run all after-step interceptors in reverse order."""
    for interceptor in reversed(interceptors):
        await _safe_invoke_interceptor(interceptor, strict, step_context, state)


async def run_on_error_interceptors(
    interceptors: tuple[_WorkflowInterceptor, ...],
    step_context: WorkflowStepContext,
    state: WorkflowState,
    error: Exception,
    *,
    strict: bool = False,
) -> None:
    """Run all on-error interceptors in reverse order."""
    for interceptor in reversed(interceptors):
        await _safe_invoke_interceptor(interceptor, strict, step_context, state, error)


async def _safe_invoke_interceptor(
    interceptor: _WorkflowInterceptor,
    strict: bool,
    *args: Any,
) -> None:
    """Safely invoke an interceptor, handling exceptions based on strict mode."""
    try:
        result = interceptor.fn(*args)
        if inspect.isawaitable(result):
            await result
    except Exception:
        if strict:
            raise
        logger.exception("Workflow interceptor failed: %s", interceptor.name or interceptor.interceptor_id)
