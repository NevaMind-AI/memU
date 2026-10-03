# 0019: Allocate a Private Workspace for Each Developer Memorize Run

## Status

Accepted.

## Context

Developer applications submit 1–10 canonical sessions through `memu memorize prepare`,
run an external executor, and commit once. A shared `~/.memu/developer` workspace
couples independent invocations: a pending or failed executor blocks the next run,
and callers cannot address each run independently.

Related: https://github.com/MrXnneHang/xnnehang.top/issues/183

## Decision

The developer CLI allocates one private directory per prepare invocation using
`tempfile.mkdtemp` below `~/.memu/developer/runs/`. Atomic allocation gives concurrent
prepares distinct paths. Its basename is the opaque run id returned with the
workspace, transcript paths, ordered jobs, executor prompt, and next command.
A batch of N sessions remains one run with 2N + 1 serial jobs.

`commit <run-id>`, internal `verify-resources <run-id>`, and `discard <run-id>`
resolve only ids below that root. Path syntax and links redirecting the run
outside its allocated location are rejected. Callers cannot select arbitrary
workspace paths through the CLI.

Each run retains the existing active marker and content snapshot. Backend commit
failure preserves the run for retry. Successful commit removes the entire run
directory. Explicit discard removes a stopped run without a backend call and can
also remove an incomplete run left by process termination. Ordinary prepare
failure cleans up its newly allocated directory; there is no TTL deletion.

Allocation and complete-directory deletion belong to the CLI, which owns these
paths. The existing explicit-workspace Python lifecycle functions retain their
behavior, including leaving their caller-owned directory in place. Host adapter
prepare–commit workflows are unchanged.

## Consequences

- Applications persist the returned run id and address it explicitly on commit,
  verification, or discard. Commands never implicitly select the latest run.
- Applications coordinate one executor per run and serialize operations on that
  run. The active marker is not a process lock, and discard must follow executor
  termination.
- Separate directories prevent filesystem interference but not backend write
  conflicts. Runs updating overlapping RecallFiles must serialize the complete
  prepare–evolve–commit cycle, or use disjoint ownership. Serializing commits
  alone cannot refresh snapshots created by earlier prepares.
- The CLI change is breaking for callers using an unqualified memorize commit or
  verifier command. Complete any old fixed-workspace run with the previous CLI
  before upgrading. Old working files are not automatically moved or deleted.
- Evolve-type selection and job granularity remain independent follow-up work.
