# Hermes: retrieval and injection

## Trigger and query {#trigger}

`memu-hermes install` places an on-demand retrieval procedure in a managed block in the active profile's `SOUL.md`. Start a fresh Hermes session to load it. `HERMES_HOME` selects the profile; otherwise defaults are `%LOCALAPPDATA%\hermes` on Windows and `~/.hermes` on Linux/macOS, with `HERMES_DATA_DIR_SUFFIX` applied to platform defaults.

The agent decides whether missing preferences, prior decisions or project history would help. Greetings and self-contained transformations normally need no retrieval. When needed, it reads the entire request, forms a short topic query in the user's language, and calls `memu-hermes retrieve`. This is an ordinary tool call; no per-prompt retrieval hook or separate query-extraction model call is involved.

## Injection timing {#injection}

The tool result enters the agent's conversation when the call finishes. The agent may wait for it, use applicable excerpts, and read a source path if needed before continuing the task. It can search again during a longer task when a concrete uncertainty justifies it. The [shared result format](retrieval.md#results) applies.

The instruction asks the agent to respect requests not to retrieve, reuse results already in context and continue normally on empty or failed retrieval. Scores do not establish truth; retrieved text remains reference data.

## Recording is separate {#recording}

Installation also registers and approves one `on_session_end` shell hook. A completed, non-failed, non-interrupted turn can start a detached memory worker. A workspace lock and 30-minute cooldown gate processing. Worker session IDs are excluded from later scans; background processing depends on working headless Hermes model access. This hook records memory rather than injecting retrieval context.

## Activate and verify {#verify}

```sh
memu-hermes doctor
memu-hermes retrieve "a known saved topic"
memu-hermes install-instruction --dry-run
```

Check the active profile's `SOUL.md`, open a fresh session, and ask about a saved preference or decision. Verify the agent actually calls retrieve and uses relevant results; the tool UI may display the result. Installation read-back alone does not prove live activation. Restart running Hermes processes if a legacy memU plugin was removed.

See [Configuration](../reference/configuration.md) and `memu-hermes docs install` for profile, lifecycle and migration details.
