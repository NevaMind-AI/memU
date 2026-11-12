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
| Hermes | A managed SOUL.md block lets the agent decide when to call `memu-hermes retrieve`. Automatic hook delivery is deferred pending upstream support. | Explicit CLI bridging commands remain available; installation does not enable automatic memorization. |

Codex and Claude Code start processing available history on prompt submission;
pi coordinates pending retrieval with response completion before starting memory
processing. pi's extension lifecycle and Windows stdin handling remain documented
in ADR 0021.

### Hermes delivery limitation and current integration

Hermes was initially designed to use the same prompt-submission retrieval pattern.
The tested plugin started retrieval at `pre_llm_call`, but its injection API did
not provide the intended mid-task context delivery and rewake behavior. During an
active task, `ctx.inject_message()` queued the result until the current turn ended,
then delivered it as an independent message and model turn. Users could see raw
retrieval content presented as a user message, followed by an acknowledgment or
question rather than a useful supplement to the original task. This disrupted
the conversation instead of meeting the shared hook experience.

The alternative investigated was `ContextEngine.select_context()` (request-time
context selection). An isolated probe established structural feasibility, but
real-model behavior, provider cache usage, compression, session lifecycle and
concurrency were not sufficiently verified. It also occupies the context-engine
slot and requires adapting compression configuration. Defer this approach and
revisit automatic retrieval delivery when upstream provides a suitable mechanism
for supplemental context without a synthetic user turn.

For now, install the complete retrieval procedure in one managed SOUL.md block.
The agent decides whether missing historical information warrants retrieval and
forms a short query. Greetings and self-contained requests normally need no
search; relevant results already in the conversation should be reused. Accept
lower retrieval frequency rather than require a search on every turn. Hermes's
native memory and self-authored skills can coexist with this procedure.

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
- Hermes's explicit CLI worker sets `MEMU_BRIDGING_RUN=1` and uses the existing
  CLI-driven bridging pipeline. The SOUL.md installation does not register the
  former plugin's session-identity or automatic worker callbacks.

### Installation and verification

All four installers reuse backend configuration and `doctor --backend-only`
before installing host integration files. Host-specific checks verify the managed
hooks, extension or instruction block. These checks establish backend connectivity
and local integration state; they do not prove model/provider access.

Hermes patches SOUL.md and verifies the managed block by reading it back. It uses
CLI commands rather than importing Hermes's Python modules, and has no
plugin-specific minimum version gate. Instruction refresh preserves the local
on-demand policy. Start a fresh session to load the instruction; readback alone
does not establish that an existing session has loaded it.

Installation and removal verify legacy Windows schedule cleanup. An owned legacy
`memu-memory` plugin is removed through Hermes's CLI and checked for directory
absence. Ownership, symlink, CLI and readback failures stop migration. Restart
running Hermes processes after plugin removal to unload old callbacks.

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

Hermes retrieval is an ordinary tool call that the agent may await and the UI may
display. Autonomous retrieval coverage depends on the model; a successful query
in a focused probe does not establish reliable discovery in everyday conversation.
The service remains embedding-only and the main agent supplies the query.

Explicit memorization commands remain available, but SOUL.md installation does
not schedule automatic processing. Linux/macOS legacy schedules and Hermes native
cron still require separate inspection and verified removal. Revisit automatic
retrieval hooks after upstream context delivery supports the intended experience.

## References

- [pi extension hooks](0021-pi-extension-hooks.md)
- [Bridging self-session exclusion](0015-bridging-must-not-mine-its-own-run.md)
- [Hermes event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)
