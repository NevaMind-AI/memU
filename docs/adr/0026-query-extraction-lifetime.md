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

Run the process tests on macOS, Linux and Windows; the current upstream CI only
covers Linux. Record real pi shutdown, session switching and reload separately
from process-level tests. Codex and Claude host-exit behavior also requires its
own evidence.
