# 0022: Shared Host Hooks for Retrieval and Memorization

## Status

Accepted.

Builds on [ADR 0021: pi extension hooks](0021-pi-extension-hooks.md) and
[ADR 0015: bridging self-session exclusion](0015-bridging-must-not-mine-its-own-run.md).

## Context

Codex, Claude Code, pi and Hermes expose different lifecycle events and context
injection APIs. Their adapters share the same retrieval backend and
prepare/agent/commit pipeline. Each host binds its native events to these shared
operations while preserving the host's timing and session identity.

## Decision

### Native events and context delivery

| Host | Retrieval | Background memorization |
| --- | --- | --- |
| Codex | Asynchronous `UserPromptSubmit` hook returns `additionalContext`. | A separate `UserPromptSubmit` hook launches a detached worker. |
| Claude Code | `UserPromptSubmit` with `asyncRewake` delivers retrieved context and wakes the agent. | A separate `UserPromptSubmit` hook launches a detached worker. |
| pi | The extension starts retrieval on `input`, continues immediately, and delivers results through `sendMessage` with `steer` and `triggerTurn`. | After `agent_settled`, pending retrieval must finish before a worker starts for the persisted session's project directory. |
| Hermes | The plugin's `pre_llm_call` returns a context dictionary before inference. | `on_session_end` with `completed=True` launches a detached worker. |

Codex and Claude Code start processing available history on prompt submission;
pi and Hermes trigger after the response. pi's extension lifecycle and Windows
stdin handling remain documented in ADR 0021.

### Shared worker admission

Automatic workers and direct `hook-run` invocations enter the same admission
path before preparing jobs. An OS lock covers the entire prepare/agent/commit
pass in the host workspace. A busy workspace is skipped immediately. A persisted
startup timestamp enforces a 30-minute cooldown; failed and no-input passes also
consume cooldown. Process exit releases the lock.

The host agent processes the prepared jobs using its own configured model and
tools. The memU service remains embedding-only.

### Worker session identity

Recursion guards stop worker activity from launching more retrieval or memory
processing. Persisted worker session IDs are supplied to later `prepare` scans
as `skip_sessions`:

- Codex marks its memory agent process and records the thread ID reported in its
  output.
- Claude Code allocates a fresh session ID, passes it to the headless agent, and
  records it in the self-session list.
- pi allocates a worker session ID and carries the bridging-run guard; its memory
  agent disables extensions and session persistence.
- Hermes sets `MEMU_BRIDGING_RUN=1` on the memory agent. The plugin uses the
  `pre_llm_call` session ID to invoke `remember-self`, then skips retrieval and
  further worker launches for that process.

### Installation and verification

All four installers reuse backend configuration and `doctor --backend-only`
before installing host integration files. Host-specific checks verify the managed
hooks, extension or plugin. These checks establish backend connectivity and local
integration state; they do not prove model/provider access.

Hermes installs a managed `memu-memory` plugin under the active `HERMES_HOME`,
bound to the installing Python runtime and memU workspace. Ownership and symlink
checks guard file updates and removal. Hermes's native plugin commands handle
activation and removal bookkeeping. Restart Hermes to load or unload the plugin.

memu-cli resolves Hermes paths locally from `HERMES_HOME`, then the platform
default (`%LOCALAPPDATA%\hermes` on Windows, `~/.hermes` on POSIX). The rule is
ported from upstream HEAD
[`760112adb6458417da8614d2269e5325f0739ed5`](https://github.com/NousResearch/hermes-agent/blob/760112adb6458417da8614d2269e5325f0739ed5/hermes_constants.py)
(2026-07-25 UTC). Instructions, legacy skill cleanup, plugins and the session
store share that resolution. `remove-instruction` removes every complete
managed block for the current host while preserving other hosts' blocks.

## Consequences

Admission and pipeline behavior are shared across the four hosts. Native hook
timing, context delivery and session identity stay in each adapter.

Hermes retrieval waits up to 20 seconds and uses at most the first 2,000 prompt
characters. Its memory worker uses Hermes's configured default model/provider.
Existing scheduled tasks and standing retrieval instructions require inspection
and cleanup when switching to hooks, so they do not duplicate processing.

## References

- [pi extension hooks](0021-pi-extension-hooks.md)
- [Bridging self-session exclusion](0015-bridging-must-not-mine-its-own-run.md)
- [Hermes event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)
