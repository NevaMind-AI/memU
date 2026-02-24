# ADR 0001: Use Workflow Pipelines for Core Operations

- Status: Accepted
- Date: 2026-02-24

## Context

memU has multiple high-level operations (`memorize`, `retrieve`, and CRUD/patch operations) that each require multi-stage execution, LLM calls, storage writes, and optional short-circuit behavior.

A single monolithic function per operation would make these flows hard to extend, observe, and customize.

## Decision

Model each core operation as a named workflow pipeline composed of ordered `WorkflowStep` units.

- Register pipelines centrally in `MemoryService` via `PipelineManager`
- Validate required/produced state keys at pipeline registration/mutation time
- Execute through a `WorkflowRunner` abstraction (`local` by default)
- Support runtime customization by step-level config and structural mutation (insert/replace/remove)
- Provide before/after/on_error step interceptors for instrumentation and control

## Consequences

Positive:

- uniform execution model across memorize/retrieve/CRUD
- explicit, inspectable stage boundaries
- extension points for custom runners and step customization
- easier interception and observability around stage execution

Negative:

- dict-based workflow state relies on key naming discipline
- pipeline mutation can increase behavioral variance between deployments
- more framework code compared to direct function calls
