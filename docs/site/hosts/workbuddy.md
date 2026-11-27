# WorkBuddy: retrieval and injection

## Trigger and query {#trigger}

Follow `memu-workbuddy docs install` after configuring the backend. `memu-workbuddy install-instruction` writes the retrieval procedure inline in a managed block in `~/.workbuddy/SOUL.md`. WorkBuddy loads this global behavior file into sessions; open a new session after changing it.

The instruction asks the agent to retrieve before answering. The agent forms a focused query and runs `memu-workbuddy retrieve "<query>"` through its normal command tool. This is instruction-driven: memU does not install an automatic per-prompt retrieval hook for WorkBuddy, and the optional hook query extractor does not run here.

## Injection timing {#injection}

When retrieve finishes, its tool output becomes conversation context. The agent uses relevant excerpts and reads a returned source path only when necessary before continuing the answer. See the [shared result format](retrieval.md#results). An empty result should not stop the task.

`SOUL.md` carries the instruction, not the stored memory itself. Retrieval requires the agent to follow that instruction and execute the tool call in the current session.

## Migration and recording {#recording}

Default-path instruction installation removes the recognized legacy memU block from `~/.workbuddy/MEMORY.md` only after the new `SOUL.md` block is safely written. User-authored memory is preserved. `MEMORY.md` is not the current retrieval instruction target.

A separate bridging task processes session history on the schedule configured in the installation guide. That process records durable memory; it does not inject context into the current response. Writes and retrieval must share backend and embedding settings.

## Activate and verify {#verify}

```sh
memu-workbuddy doctor
memu-workbuddy retrieve "a known saved topic"
memu-workbuddy install-instruction --dry-run
```

Check that `SOUL.md` has one managed block and that the old memU block is absent from `MEMORY.md`. Start a fresh session and observe an actual retrieve call for known memory. Manual success proves backend access, not that WorkBuddy loaded the instruction or used the results.

See [Configuration](../reference/configuration.md) and `memu-workbuddy docs install` for full setup and scheduling.
