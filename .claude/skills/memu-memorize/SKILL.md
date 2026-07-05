---
name: memu-memorize
description: Save files or a whole workspace folder into memU's persistent memory. Use when the user asks to remember, memorize, or save something for later sessions, when they ask to sync a workspace/folder into memory, or after completing work whose context should survive this session (meeting notes, decisions, agent traces).
---

# memU: memorize a workspace or file

memU compiles sources into persistent, retrievable memory (SQLite + markdown tree). Writing requires an LLM key; make sure `OPENAI_API_KEY` (or `MEMU_LLM_PROVIDER` + matching key) is set before running, and tell the user if it is missing.

## Locate the CLI

Use the first available runner:

1. `memu` (installed via `pip install memu-py`)
2. `uvx --from memu-py memu`
3. `npx memu-cli`

## Sync a folder (preferred)

```bash
memu memorize-workspace <folder>
```

- Incremental: diffs against `<folder>/.memu_manifest.json`; only added/modified files are processed, memory from deleted files is removed. Safe to re-run.
- Top-level directory decides the treatment: `chat/` → memory topics, `agent/` → skills, everything else → indexed workspace context.
- Writes state to `./data/memu.sqlite3` and the markdown tree to `./data/memory/` (relative to CWD — run from the project root so later retrievals hit the same store).

## Memorize a single file

```bash
memu memorize <path> [--modality conversation|document|image|video|audio]
```

Modality is inferred from the extension; only pass `--modality` if the command asks for it.

## After running

Report the printed diff (added/modified/deleted) to the user. Pass `--json` instead if you need to parse the result.
