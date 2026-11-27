# Claude Code: retrieval and injection

## Trigger and query {#trigger}

`memu-claude-code install` writes two `UserPromptSubmit` commands to `~/.claude/settings.json`. The retrieval hook uses `asyncRewake: true` and `prompt-hook --rewake`; the second command admits background memorization. Open a new Claude session to load the hooks.

The retrieval hook skips automatic events, empty prompts and its own memorization runs. Other prompts follow the shared [query policy](retrieval.md#query). Extraction defaults off. When enabled for a long prompt, it uses an isolated standalone Claude request with tools, MCP servers and hooks disabled and no session persistence. The 12-second extraction deadline is part of the retrieval work budget.

## Injection timing {#injection}

The installed `--rewake` mode writes retrieved context to stderr and exits with status 2 so Claude's asynchronous hook mechanism can wake the agent with that context, potentially after its initial response. This exit is the deliberate context-delivery signal. Calling `prompt-hook` without `--rewake` instead returns the structured `additionalContext` JSON form.

Context fits a budget of 9,500 UTF-16 units, including its prefix and JSON. The hook keeps complete entries, considering hits before resources, and reports returned/omitted counts. Oversized entries are omitted rather than cut mid-entry. Empty successful retrieval can still produce completion/status context; failure produces a local diagnostic and no retrieved context.

## Recording is separate {#recording}

The background-memory hook also runs on submit. Its detached worker uses admission checks, locking and cooldown; hook registration does not prove processing completed. Keep recording and retrieval on the same backend and review user-managed historical schedules for duplicates.

## Activate and verify {#verify}

```sh
memu-claude-code doctor
memu-claude-code retrieve "a known saved topic"
```

Start a fresh Claude session, send a relevant message, and inspect `~/.memu/hosts/claude-code/log/hooks/retrieve/` (or a custom base directory). Check status, `additional_context`, budget and omission counts. Local settings read-back proves registration only; observing context delivery verifies host execution. Model-request authentication checks are separate from installation success.

See [Configuration](../reference/configuration.md) and `memu-claude-code docs install` for setup details.
