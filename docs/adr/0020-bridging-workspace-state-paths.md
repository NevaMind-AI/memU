# 0020: Separate Bridging Workspace Paths from Stable Host State

## Status

Proposed for the Codex integration branch. This change supplies path separation;
CLI run allocation and recovery policy remain follow-up decisions.

## Context

Bridging currently puts session slices, jobs, editable recall files, their hash
baseline, and pending cursor beside the promoted cursor and self-session registry.
Allocating a private directory by changing that one root would also move durable
progress, admission locks, cooldown, and diagnostics into each run.

The developer entry point already has its own `MemorizeWorkspace` and lifecycle
(ADR 0019). Hosts share `Layout` and the bridging pipeline. Codex contributes
session adaptation and worker admission/execution; it does not need another
workspace manager. The broader lifecycle consolidation is tracked in
[plan #206](https://github.com/MrXnneHang/xnnehang.top/issues/206).

## Decision

Extend the existing bridging `Layout` with an optional `state_base`. `base`
continues to mean the editable workspace. `layout.state` resolves to
`state_base`, falling back to `base` for all existing callers.

| Workspace (`base`) | Stable host state (`state`) |
| --- | --- |
| `sessions/`, `jobs/` | Promoted session cursor |
| `memory/`, `skill/`, hash baseline | Self-session registry |
| Pending session cursor, cycle marker | Codex whole-pass lock and cooldown |
| Resource log and annotated resources | Codex worker logs |

The shared pipeline reads the stable cursor, stages progress in the workspace,
and promotes it only after a successful backend commit, including no-op success.
It creates the stable cursor's parent before promotion. Cursor promotion uses
`os.replace`, so workspace and stable state must be on the same filesystem.
Future host runs below `<host-base>/runs/` satisfy that constraint.

Codex admission and logging use `layout.state`; the evolve process still uses
`layout.base` for its working directory. The existing thread registration follows
`layout.self_sessions` into stable state.

This is path routing within the existing implementation. It adds no allocator,
run registry, command, cleanup policy, or Codex lifecycle. Existing CLI calls
continue to construct the default layout, so their paths and behavior stay the
same. Developer code is unchanged.

## Coordination and follow-up

Callers must serialize the complete prepare/evolve/commit cycle for a stable
state root. Separate outputs do not claim input: two prepares before either
commit select the same increment. A stale pending manifest can also overwrite
newer progress if a caller later commits it. The Codex whole-pass lock remains
at the stable root even when passed distinct workspaces.

Activating private runs through the CLI requires an agreed manual run-id and
unfinished-run policy, explicit base/run addressing in generated verifier
commands, and handling of existing shared-directory work. Direct prepare and
commit currently do not acquire the Codex admission lock; this change does not
make them safe concurrent callers.

Backend acknowledgement followed by local-finalization failure remains a
recovery gap in bridging. Path separation does not introduce automatic retries,
claim exactly-once delivery, or change which artifacts successful commit clears.
These decisions belong to the next lifecycle work under
[plan #211, sections 9.5 and 10](https://github.com/MrXnneHang/xnnehang.top/issues/211).
