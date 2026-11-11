# 0021: pi Extension Hooks for Retrieval and Memorization

## Status

Accepted.

## Context

pi exposes extension events and custom context messages. Its input handlers are
awaited, so waiting for retrieval there would delay the user's first model call.
The existing host bridging pipeline already owns preparing sessions, processing
jobs and committing memory.

## Decision

Package a TypeScript extension with memu-cli and install it through
`memu-pi install`. The installer reuses the shared backend configuration and
verification lifecycle, checks the existing pi executable on PATH, and verifies
the installed extension by reading it back. Reload pi to activate it.

The extension starts the Python retrieval command from `input` and immediately
continues. Successful results use `sendMessage` with `triggerTurn` and `steer`;
this queues context during a response and resumes an idle agent. Session shutdown
cancels outstanding retrieval processes and invalidates callbacks.

Track user input separately from custom context delivery. After `agent_settled`,
once pending retrieval has completed, launch one detached memorization worker
for the persisted session's project directory. The worker reuses the shared
prepare/agent/commit pipeline, workspace lock and cooldown. Its pi process uses
the active session's provider and model, disables extensions and session
persistence, and carries the bridging-run guard.

Pass the short job-directory instruction through pi's native prompt argument and
use `DEVNULL` for stdin. On Windows, pi can hang when reading the temporary-file
stdin used by other host workers.

## Consequences

Retrieval can update context after the first response. Memorization starts after
the completed response and its retrieval continuation, and custom context alone
does not schedule another worker. Ephemeral sessions have no transcript to mine.
The extension uses pi's configured runtime and model.
