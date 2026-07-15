# memu-cli

> 🚧 **Under heavy construction** — memU is undergoing a major rework; commands and flags may change. Expected to stabilize around **July 15, 2026**.

CLI for [memU](https://github.com/NevaMind-AI/MemU) — personal memory as files: fast retrieval, higher accuracy, lower cost.

This package is a thin launcher. The engine is the PyPI package [`memu-cli`](https://pypi.org/project/memu-cli/) (the CLI release channel of [`memu-py`](https://pypi.org/project/memu-py/), Python ≥ 3.13); the shim delegates to `uvx`, `pipx run`, or an installed `python3 -m memu`, in that order. Install [uv](https://docs.astral.sh/uv/) for the smoothest zero-setup experience — `uvx` fetches both a Python 3.13 runtime and the engine automatically, no preinstalled Python required:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux
# or on Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Usage

```bash
export OPENAI_API_KEY=sk-...

# diff-sync a workspace folder (chat/ -> memory, agent/ -> skills, other -> index)
npx memu-cli memorize-workspace ./workspace

# single-shot embedding retrieval (LLM-free, fast)
npx memu-cli retrieve-workspace "deploy checklist"

# rebuild the INDEX.md / MEMORY.md / SKILL.md markdown tree
npx memu-cli export

# legacy pair: memorize a single file / LLM-routed retrieval
npx memu-cli memorize notes/meeting.md
npx memu-cli retrieve "What are this user's launch preferences?"
```

State persists in a local SQLite database (`./data/memu.sqlite3` by default), so memorize in one invocation and retrieve in the next. Run `npx memu-cli --help` or see the [main README](https://github.com/NevaMind-AI/MemU#readme) for all flags and `MEMU_*` environment variables.

## License

Apache-2.0
