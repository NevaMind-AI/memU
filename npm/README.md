# memu-cli

CLI for [memU](https://github.com/NevaMind-AI/MemU) — personal memory as files: fast retrieval, higher accuracy, lower cost.

This package is a thin launcher. The engine is the Python package [`memu-py`](https://pypi.org/project/memu-py/) (Python ≥ 3.13); the shim delegates to `uvx`, `pipx run`, or an installed `python3 -m memu`, in that order. Install [uv](https://docs.astral.sh/uv/) for the smoothest zero-setup experience.

## Usage

```bash
export OPENAI_API_KEY=sk-...

# memorize a single file (modality inferred from the extension)
npx memu-cli memorize notes/meeting.md

# diff-sync a workspace folder (chat/ -> memory, agent/ -> skills, other -> index)
npx memu-cli memorize-workspace ./workspace

# LLM-routed retrieval (heavy, high quality)
npx memu-cli retrieve "What are this user's launch preferences?"

# single-shot embedding retrieval (LLM-free, fast)
npx memu-cli retrieve-workspace "deploy checklist"

# rebuild the INDEX.md / MEMORY.md / SKILL.md markdown tree
npx memu-cli export
```

State persists in a local SQLite database (`./data/memu.sqlite3` by default), so memorize in one invocation and retrieve in the next. Run `npx memu-cli --help` or see the [main README](https://github.com/NevaMind-AI/MemU#readme) for all flags and `MEMU_*` environment variables.

## License

Apache-2.0
