# Cursor: retrieval and injection

## Trigger and query {#trigger}

Cursor uses an instruction in each project's root `AGENTS.md`. After configuring the backend, follow `memu-cursor docs install`; run `memu-cursor install-instruction` from the project root to install the managed block. Repeat for each project that should use memory. A different checkout without the block does not inherit it automatically.

The loaded instruction asks the agent to retrieve before answering. The agent forms a focused query from the user's request and runs `memu-cursor retrieve "<query>"` through its normal command tool. memU does not register an automatic per-prompt retrieval hook for Cursor, and this path does not use the optional hook query extractor.

## Injection timing {#injection}

The retrieve command's tool output becomes context when the command completes. The agent uses relevant results before composing or continuing its answer, opening a returned path only when the excerpt is insufficient. The [shared result format](retrieval.md#results) applies. An empty result lets the agent continue normally.

This depends on Cursor loading the project's `AGENTS.md` and the agent following it. Installing a background schedule alone does not provide the retrieval instruction.

## Recording is separate {#recording}

The installation guide configures a bridging task to process session history using the standalone `cursor-agent` CLI. That task writes memory on its configured schedule; it does not inject context into the active conversation. New conversation content is searchable only after processing and commit complete.

## Activate and verify {#verify}

```sh
memu-cursor doctor
memu-cursor retrieve "a known saved topic"
memu-cursor install-instruction --dry-run
```

Run these from the intended project. Inspect its `AGENTS.md` for one memU managed block and preserved user content. Start a fresh project session, ask about known memory, and verify the actual retrieve tool call and result use. Manual retrieval proves backend access, not that Cursor loaded the instruction.

See [Configuration](../reference/configuration.md) and `memu-cursor docs install` for the full setup, including scheduling prerequisites.
