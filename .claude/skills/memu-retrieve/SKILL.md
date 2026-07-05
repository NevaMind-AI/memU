---
name: memu-retrieve
description: Search memU's persistent memory for context from earlier sessions. Use when the user asks what is known/remembered about a person, project, or topic, when starting a task that likely has prior context (preferences, decisions, past attempts), or when the user references something not in the current conversation.
---

# memU: retrieve memory

memU stores memory in a local store (`./data/memu.sqlite3` + `./data/memory/` markdown tree, relative to CWD). Retrieval embeds the query, so an API key must be set (`OPENAI_API_KEY` by default).

## Locate the CLI

Use the first available runner:

1. `memu` (installed via `pip install memu-py`)
2. `uvx --from memu-py memu`
3. `npx memu-cli`

## Fast search (default)

```bash
memu retrieve-workspace "<query>"
```

Single-shot embedding search, no LLM calls. Returns JSON with three layers:

- `segments` — the matched slices, ranked by similarity (check `score`)
- `files` — the memory/skill documents those segments belong to (usually what you want)
- `resources` — matching raw sources, when summaries are not enough

## Deep retrieval (when fast search misses)

```bash
memu retrieve "<query>"
```

LLM-routed: rewrites the query, ranks per layer, checks sufficiency. Slower and costs LLM calls — use only when the fast path returns nothing relevant or the question needs reasoning over scattered memories.

## Notes

- Run from the project root so the CLI hits the store that `memu-memorize` wrote.
- Low scores across the board usually mean nothing relevant is stored — say so rather than stretching weak matches.
- You can also read `./data/memory/MEMORY.md` / `SKILL.md` / `INDEX.md` directly for a browsable overview.
