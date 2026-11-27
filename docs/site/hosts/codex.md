# Codex: retrieval and injection

## Trigger and query {#trigger}

`memu-codex install` registers retrieval and background-memory commands under `UserPromptSubmit` in the selected Codex home's `hooks.json`. It uses app-server to register trust and checks that Codex reports asynchronous retrieval. The default home is `~/.codex`; use the same home/profile for installation and runtime.

Every nonempty submitted prompt starts retrieval without waiting for memory before the initial answer. The hook follows the shared [query policy](retrieval.md#query): extraction defaults off, with an 800-character prefix; enabling extraction uses an isolated, ephemeral Codex request with hooks and rules disabled. It inherits the selected Codex configuration and has a 12-second extraction deadline.

## Injection timing {#injection}

After retrieval completes, the hook returns `hookSpecificOutput.additionalContext` for `UserPromptSubmit`. Codex controls when that asynchronous context is consumed; the initial response can already be underway. Context contains query metadata, retrieve subprocess timing, hits, resources and delivery counts. The hook sets no additional-context size limit (`additionalContextLimit: 0`); hits are still capped at five.

An empty result still returns completion metadata. A failed retrieval logs the error and returns no memory context; it does not block the user's original request. Retrieved text is reference data.

## Recording is separate {#recording}

The second submit hook starts detached background memorization, subject to admission checks, a workspace lock and cooldown. It processes conversation history independently of retrieval; the prompt being answered is not guaranteed to be saved or searchable immediately. User-managed legacy schedules should be checked to avoid duplicate processing.

## Activate and verify {#verify}

```sh
memu-codex doctor
memu-codex retrieve "a known saved topic"
```

Send another message after installation and inspect `~/.memu/hosts/codex/log/hooks/retrieve/` (or your custom base directory). Check the query, `extraction_status`, counts and `additional_context`; keep trace contents private. Installer trust checks and manual retrieval do not prove delivery in a running session. If the current client has not loaded the hooks, start a fresh session and verify an actual submit event.

See [Configuration](../reference/configuration.md) for backend and query options, and `memu-codex docs install` for the packaged installation guide.
