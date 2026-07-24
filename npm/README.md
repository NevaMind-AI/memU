# memu-cli

CLI for [memU](https://github.com/NevaMind-AI/MemU) — personal memory as files. Persist agent-prepared memory and skill documents, then retrieve compact, ranked context instead of restuffing every prompt. Embedding-only: no LLM call happens inside memU.

## Quick start

The only prerequisite is [uv](https://docs.astral.sh/uv/) — it fetches both a Python 3.13 runtime and the memU engine automatically, so nothing else needs to be preinstalled:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # macOS / Linux
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then:

```bash
export OPENAI_API_KEY=sk-...

# persist prepared memory: {"recall_files": [...], "resource": [...]}
npx memu-cli commit results.json

# list every stored memory/skill file
npx memu-cli list-files

# single-shot embedding retrieval — LLM-free, fast
npx memu-cli retrieve "deploy checklist"
```

By default, state persists in a local SQLite database
(`./data/memu.sqlite3`). Set `MEMU_MEMORY_MODE=cloud` and
`MEMU_CLOUD_API_KEY=<project-api-key>` to run the same commands through MemU
Cloud instead; the production API base defaults to
`https://api.memu.so/api/v4/memory/` and can be overridden with
`MEMU_CLOUD_BASE_URL` (for example,
`https://staging-api.memu.so/api/v4/memory/`). Local embedding settings remain
separate (`MEMU_EMBED_PROVIDER`, `MEMU_EMBED_MODEL`, `MEMU_DB`, ...). Cloud
currently persists memory and skill recall files but not submitted workspace
resources. Run `npx memu-cli <command> --help` for the local-mode flags.

## Commands

| Command | Alias | What it does |
|---|---|---|
| `retrieve <query>` | `search` | Rank memory segments, files, and resources by embedding similarity — zero LLM calls |
| `list-files` | | List every recall file across the memory and skill tracks |
| `commit <payload.json>` | | Persist externally-prepared recall files and resources (`-` reads stdin) |

## How it works

This npm package is a thin launcher (a few kB, no dependencies). The engine is the PyPI package [`memu-cli`](https://pypi.org/project/memu-cli/) — the memU engine itself, with prebuilt wheels for Linux (x86_64/aarch64), macOS (Intel/Apple Silicon), and Windows. The shim finds a runner and delegates, in order:

1. `$MEMU_PYTHON -m memu` — explicit interpreter override
2. `uvx --from memu-cli memu` — no install needed, cached by uv (recommended)
3. `pipx run --spec memu-cli memu` — no install needed, cached by pipx
4. `python3 -m memu` — requires `pip install memu-cli`

Using Python already? Skip npm entirely: `uvx --from memu-cli memu --help`, or `pip install memu-cli`. The same package carries the library API (`MemoryService`, Postgres backends) — one install covers CLI, host adapters, and library use.

See the [main README](https://github.com/NevaMind-AI/MemU#readme) for the memory model, library API, and self-hosting options.

## License

Apache-2.0
