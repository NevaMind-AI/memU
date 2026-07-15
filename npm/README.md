# memu-cli

CLI for [memU](https://github.com/NevaMind-AI/MemU) — personal memory as files. Compile conversations, documents, and agent traces into a Markdown memory tree (`INDEX.md` / `MEMORY.md` / `SKILL.md`), then retrieve compact, ranked context instead of restuffing every prompt.

> 🚧 memU is under active rework; the workspace pair below is the primary surface, other commands and flags may still change.

## Quick start

The only prerequisite is [uv](https://docs.astral.sh/uv/) — it fetches both a Python 3.13 runtime and the memU engine automatically, so nothing else needs to be preinstalled:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # macOS / Linux
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then:

```bash
export OPENAI_API_KEY=sk-...

# diff-sync a workspace folder into memory
# (chat/ -> memory topics, agent/ -> skills, everything else -> indexed context)
npx memu-cli memorize-workspace ./workspace

# single-shot embedding retrieval — LLM-free, fast
npx memu-cli retrieve-workspace "deploy checklist"

# rebuild the INDEX.md / MEMORY.md / SKILL.md markdown tree
npx memu-cli export
```

State persists in a local SQLite database (`./data/memu.sqlite3` by default), so memorize in one invocation and retrieve in the next. Every flag has a `MEMU_*` environment variable (`--provider`/`MEMU_LLM_PROVIDER`, `--model`/`MEMU_CHAT_MODEL`, `--db`/`MEMU_DB`, ...) — run `npx memu-cli <command> --help` for the full list.

## Commands

| Command | Alias | What it does |
|---|---|---|
| `memorize-workspace <folder>` | `sync` | Diff-sync a folder into memory; only changed files are reprocessed |
| `retrieve-workspace <query>` | `search` | Rank memory segments, files, and resources by embedding similarity — zero LLM calls |
| `export` | | Rebuild the markdown memory tree from the store |
| `memorize <file>` / `retrieve <query>` | | Legacy single-file pair — LLM-routed, heavier; prefer the workspace pair |

## How it works

This npm package is a thin launcher (a few kB, no dependencies). The engine is the PyPI package [`memu-cli`](https://pypi.org/project/memu-cli/) — the CLI release channel of [`memu-py`](https://pypi.org/project/memu-py/), same module, versioned independently, with prebuilt wheels for Linux (x86_64/aarch64), macOS (Intel/Apple Silicon), and Windows. The shim finds a runner and delegates, in order:

1. `$MEMU_PYTHON -m memu` — explicit interpreter override
2. `uvx --from memu-cli memu` — no install needed, cached by uv (recommended)
3. `pipx run --spec memu-cli memu` — no install needed, cached by pipx
4. `python3 -m memu` — requires `pip install memu-cli`

Using Python already? Skip npm entirely: `uvx --from memu-cli memu --help`, or `pip install memu-cli`. For the library API (`MemoryService`, LangGraph integration, Postgres backends), use [`memu-py`](https://pypi.org/project/memu-py/) — but install only one of the two in a given environment; they ship the same `memu` module.

See the [main README](https://github.com/NevaMind-AI/MemU#readme) for the memory model, library API, and self-hosting options.

## License

Apache-2.0
