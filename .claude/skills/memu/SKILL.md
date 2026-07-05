---
name: memu
description: Give this agent persistent memory via memU. Use to memorize (save files/folders so context survives this session) when the user asks to remember or sync something, or after completing work worth keeping; and to retrieve (search memory from earlier sessions) when the user asks what is known about a person/project/topic or references context not in this conversation.
---

# memU: memorize and retrieve persistent memory

memU compiles sources into a persistent local store (`./data/memu.sqlite3` + a browsable `./data/memory/` markdown tree, relative to CWD). What one session memorizes, the next can retrieve — always run from the project root so every command hits the same store.

Both directions need an API key: make sure `OPENAI_API_KEY` (or `MEMU_LLM_PROVIDER` + its matching key) is set, and tell the user if it is missing.

## Locate the CLI

Use the first available runner:

1. `memu` (installed via `pip install memu-py`)
2. `uvx --from memu-py memu`
3. `npx memu-cli`

## Memorize

Sync a folder (preferred — incremental and safe to re-run):

```bash
memu memorize-workspace <folder>
```

- Diffs against `<folder>/.memu_manifest.json`: only added/modified files are processed, memory from deleted files is removed.
- Top-level directory decides the treatment: `chat/` → memory topics, `agent/` → skills, everything else → indexed workspace context.

Or memorize a single file (modality inferred from the extension):

```bash
memu memorize <path> [--modality conversation|document|image|video|audio]
```

Report the printed diff (added/modified/deleted) to the user; pass `--json` if you need to parse the result.

## Retrieve

Fast search first (single-shot embedding ranking, no LLM calls):

```bash
memu retrieve-workspace "<query>"
```

Returns JSON in three layers: `segments` (matched slices with scores), `files` (the memory/skill documents they belong to — usually what you want), `resources` (raw sources, when summaries are not enough).

If the fast path returns nothing relevant, escalate to deep retrieval (LLM-routed query rewriting + ranking + sufficiency checks — slower, costs LLM calls):

```bash
memu retrieve "<query>"
```

Low scores across the board usually mean nothing relevant is stored — say so rather than stretching weak matches. You can also read `./data/memory/MEMORY.md` / `SKILL.md` / `INDEX.md` directly for a browsable overview.
