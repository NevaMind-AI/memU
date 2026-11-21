# 0026: Own Query Extraction Beyond the Hook Lifetime

- Status: Proposed
- Task: [#790 / task-005](https://github.com/NevaMind-AI/memU/issues/790)
- Related: [ADR 0021](0021-pi-extension-hooks.md), [ADR 0022](0022-host-memory-hooks.md)
- [中文](0026-query-extraction-lifetime.zh.md)

## Confirmed scope

Query extraction must be cleaned up when its hook Python process is forcibly
terminated, as well as during ordinary cancellation and the existing 12-second
timeout.

All three extraction adapters use the shared `run_extraction()`. pi invokes it
from an `asyncio.to_thread()` worker and ends retrieval Python processes with
`child.kill()` on session shutdown. A shared Python signal handler cannot be
installed from that worker, and a forcibly terminated process cannot execute its
own `finally` cleanup. Task ownership therefore needs a lifetime boundary that
survives hook termination.

Cancellation invalidates retrieval work: it must not start prefix fallback or
deliver old context. Actual extraction errors and the normal timeout retain
their existing fallback behavior. Preserve the shared extraction input/output,
host environment, non-blocking pi input, and session-generation delivery guards.

## Decision

Use one short-lived, standard-library Python runner per extraction. A startup
gate prevents the host CLI from running before its ownership boundary is ready.
Keep prompts and environment credentials out of the new command-line protocol;
preserve raw input/output bytes, target arguments, working directory and exit
classification.

On POSIX, the runner survives the hook in its own session, monitors a dedicated
parent-lifetime pipe, and owns a separate process group for the actual extractor.
Only the hook holds the pipe's write end. On Windows, the hook owns a
non-inheritable kill-on-close Job handle and assigns the gated runner before
releasing the startup gate. CLI descendants inherit that Job.

Keep the existing 12-second extraction deadline, including runner startup. pi
coroutine cancellation must explicitly cancel its running extraction, because
cancelling `to_thread()` alone leaves its thread alive. Preserve ordinary timeout
and nonzero-exit exception classification; cancellation is a separate outcome.

If setup fails, skip the host CLI and use the existing prefix fallback. Every
outcome ends the processes owned by this extraction, including descendants that
outlive a successful or nonzero CLI exit.

The cleanup guarantee covers this task's process group or Job. A POSIX
guardian that is itself killed, deliberately detached descendants and unrelated
shared services are outside that boundary. Process cleanup does not prove that a
remote model request has stopped.

## Validation plan

Use local synthetic extraction programs and temporary paths. Cover success,
nonzero exit, timeout, active cancellation, forced hook termination, repeated
cleanup, startup races, multi-level descendants and an unrelated control process.
Exercise the pi worker-thread path and assert cancellation never invokes
retrieval fallback or delivers an old result.

Run the process tests on macOS, Linux and Windows. Record real host behavior
separately from process-level tests.

## Real host exit checks

Tested runtime commit `89810e1` on macOS 26.6.2 (arm64). The actual hosts ran
the memU `UserPromptSubmit` entry points with Codex `async: true` and Claude
Code `asyncRewake: true` plus `--rewake`. Each run used a temporary workspace,
loopback model and memory endpoints, and a synthetic extractor supplied at the
executable discovery boundary. The extractor started a sleeping descendant and
reported its PID before the test stopped the host. The fixture recorded memory
requests and checked for a unique context marker in the hook and host output.

| Host and action | Observed exit and delivery |
| --- | --- |
| Codex CLI `0.169.0-alpha.11.1`, successful `exec --ephemeral` control | The hook logged `context_returned`. The second local `/v1/responses` request carried the unique context marker. The host exited with status 0 and the hook, runner, extractor and descendant were stopped. |
| Codex CLI `0.169.0-alpha.11.1`, normal exit with extraction still active | After the local model completed its reply, the host exited with status 0. The hook, runner, extractor and descendant were stopped at the observation 2 seconds after exit. There were no memory searches, context markers or completed hook traces. |
| Codex CLI `0.169.0-alpha.11.1`, `SIGINT` during `exec --ephemeral` | Host exited with status 1. The hook, extractor and descendant were stopped at the observation 2 seconds after exit. The model request reached the local endpoint. No memory search or completed hook trace was observed after cancellation. |
| Codex CLI `0.169.0-alpha.11.1`, `SIGKILL` sent only to the host | Host exited with status -9. The hook and extraction tree were still running 2 seconds later. The fixture observed no memory search or context marker before cleaning up its processes. |
| Claude Code `2.1.303`, normal `-p --input-format stream-json` shutdown | The local model replied while extraction was active. After stdin EOF, the host and extraction tree were still running at 2 seconds. Once the fixture released the extractor, the hook completed and the host exited with status 0. The hook, runner, extractor and descendant were all stopped. The sole model request carried no context marker. |
| Claude Code `2.1.303`, `SIGTERM` during `-p` | Host exited with status 143. The hook, runner, extractor and descendant were stopped at the 600 ms observation. Zero memory searches and no context marker were observed. |
| Claude Code `2.1.303`, `SIGKILL` sent only to the host | Host exited with status -9 and left the hook and its extraction tree alive. Sending `SIGTERM` to that test hook then stopped the runner, extractor and descendant. Zero memory searches and no context marker were observed in this sequence. |

The Claude Code positive control returned the context marker from the local
memory endpoint. The real hook logged `context_returned`, and the host exposed
the marker in its `UserPromptSubmit operation blocked by hook:` output. This
verified the hook-to-host observation path for `-p` on this version.

The same Codex version also passed the normal exit with active extraction in
an isolated Linux arm64 container. All four processes were stopped by the time
the host exited. The fixture received one model request without the context
marker and zero memory searches.

The cleanup trigger is the hook's exit. A host-only force kill that leaves
the hook alive also leaves its lifetime channel open.
