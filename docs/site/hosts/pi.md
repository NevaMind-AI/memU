# pi: retrieval and injection

## Trigger and query {#trigger}

`memu-pi install` installs the managed extension at `~/.pi/agent/extensions/memu-retrieval.ts`, or under `PI_CODING_AGENT_DIR` when configured. Run `/reload` or start a new session to load it.

On `input`, the extension starts `prompt-hook` asynchronously and returns `continue`, so the main response can begin immediately. It ignores extension-origin input, empty text and bridging runs. Query selection uses the shared [query policy](retrieval.md#query). Optional extraction launches an isolated pi request with the current provider/model, no tools, extensions, skills or context files, and no saved session. Extraction defaults off and has a 12-second deadline.

## Injection timing {#injection}

Once retrieval returns a nonempty context string, the extension sends a hidden `memu-retrieval` message with `deliverAs: "steer"` and `triggerTurn: true`. The result can enter a running turn or trigger further processing after the initial response; it is not guaranteed to precede the first answer. A successful empty search still has a rendered status context.

On session shutdown, the extension stops tracked retrieval children and invalidates callbacks. It also checks session identity before delivering results. Failed hooks produce a warning instead of memory context.

## Recording after settling {#recording}

A submitted user input marks memorization pending. `agent_settled` starts the memory hook only when pi is idle and all tracked retrievals have completed. Detached workers use a shared workspace lock and a 30-minute cooldown. This does not promise a memory commit after every response; admitted processing still needs working provider access.

## Activate and verify {#verify}

```sh
memu-pi doctor
memu-pi retrieve "a known saved topic"
```

Reload the extension, send a real prompt, and inspect `~/.memu/hosts/pi/log/hooks/retrieve/` (or a custom base directory). Look for the query source, status and returned context. The injected message has `display: false`, so absence of a visible chat message is expected; verify actual context use and diagnostics. Treat trace contents as private.

See [Configuration](../reference/configuration.md) and `memu-pi docs install` for setup details.
