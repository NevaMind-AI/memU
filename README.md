![memU Banner](assets/banner.png)

<div align="center">

# memU

### Personal memory, stored as an LLM wiki

**Across Sessions. Across Agents. Across Devices.**

[![PyPI version](https://badge.fury.io/py/memu-cli.svg)](https://badge.fury.io/py/memu-cli)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</div>

---

memU is a lightweight, agent-driven memory system that gives users a shared LLM wiki across sessions, agents, and devices. It automatically distills reusable skills from the user's agent sessions. Its core memory logic is only 500 lines — compact enough to inspect, understand, and adapt. It uses embedding-only retrieval with fully pluggable storage and embedding infrastructure.

## Quick start

**Installation is agent-driven.** The guides are written for the agent, not for you. Choose Cloud or Local, then send your agent one message:

**Cloud (coming soon)**

> Read https://memu.pro/SKILL.md and follow it to install memU.

Sign in at [memu.so](https://memu.so) to view your memory files.

**Local / self-hosted**

> Read https://raw.githubusercontent.com/NevaMind-AI/MemU/main/SKILL.md and follow it to install memU.

It works for Codex, Claude Code, Cursor, OpenClaw, Hermes, WorkBuddy — and any other agent, via detection. Details in [Host adapters](#host-adapters-memory-for-desktop-coding-agents).

## How it works

![memU memory system architecture](assets/structure-v2.png)


## Host adapters: memory for desktop coding agents

memU runs as a sidecar to a desktop agent (ADR 0008/0009/0010), one binary per host. Each binds two seams:

- **record** — a scheduled bridging task slices new session logs into self-contained job files; the agent itself distills them into memory/skill Markdown; `commit` submits whatever the agent left on disk back through `commit_results`.
- **inject** — a standing instruction in the host's instruction file tells the agent to run `<binary> retrieve` (→ `progressive_retrieve`) before answering.

| Host | Binary | Session log it mines | Instruction file it patches |
| --- | --- | --- | --- |
| Codex | `memu-codex` | `~/.codex/sessions/**/*.jsonl` | `~/.codex/AGENTS.md` |
| Claude Code | `memu-claude-code` | `~/.claude/projects/<project>/<session>.jsonl` | `~/.claude/CLAUDE.md` |
| Cursor (Agent/CLI) | `memu-cursor` | `~/.cursor/projects/<project>/agent-transcripts/**.jsonl` | `./AGENTS.md` (per project) |
| OpenClaw | `memu-openclaw` | `~/.openclaw/agents/<agentId>/sessions/*.jsonl` | `~/.openclaw/workspace/AGENTS.md` |
| Hermes Agent | `memu-hermes` | `~/.hermes/state.db` (SQLite, read-only) | `~/.hermes/SOUL.md` |
| WorkBuddy | `memu-workbuddy` | `~/.workbuddy/projects/<project>/<session>.jsonl` | `~/.workbuddy/MEMORY.md` |
| **any other agent** | `memu-agent` | found by `memu-agent detect` (JSONL dialect sniffed) | found by `detect` (AGENTS.md / CLAUDE.md / SOUL.md / …) |

For agents without a dedicated binary, `memu-agent detect` probes the machine and reports per agent whether **memorization** works (a recognizable session log exists) and whether **retrieval** works (an instruction file exists to patch) — then the same verbs run against what it found.

All hosts share one store and one embedding space via `~/.memu/config.env` — what one host's sessions taught memU, another host retrieves.

Installation is the one-message setup at the top of this README. [SKILL.md](SKILL.md) is the routing skill it hands your agent: install the package, identify which host you are (falling back to `memu-agent detect` for anything without a dedicated adapter), print that host's packaged install guide (`<binary> docs install`), and follow it — configure the store, register the scheduled bridging task, patch the instruction file, each step behind a verify gate — then report which seams (memorization / retrieval) are now active.

Afterwards `<binary> doctor` proves the whole loop resolves: config, store, and a live retrieval.

Adding another host means implementing one `TranscriptSource` (where its session logs live, how its records are shaped) plus a `HostSpec`-sized CLI — the pipeline, verbs, and instruction text are shared.

## CLI

With memU Cloud, sign in at [memu.so](https://memu.so) to view your memory files. With a local installation, memory lives in the shared store configured by `MEMU_DB` in `~/.memu/config.env` — typically `~/.memu/memu.sqlite3` for local SQLite, or a Postgres DSN.

Once installed, your agent retrieves relevant memory automatically before answering. To retrieve manually, run the adapter for your host:

```bash
memu-codex retrieve "What should I remember about this project?"
# or: memu-claude-code / memu-cursor / memu-openclaw / memu-hermes / memu-workbuddy / memu-agent
```

Install or invoke the CLI directly:

```bash
pip install memu-cli         # library + memu + memu-codex CLIs
npx memu-cli --help          # CLI via npm launcher (engine: PyPI package memu-cli)
uvx --from memu-cli memu     # CLI via uv, no install
```

## Configuration

Values resolve in order: process env → `~/.memu/config.env` → default. Every CLI flag has a matching variable:

| Setting | Env var | Default |
|---|---|---|
| Store | `MEMU_DB` | `./data/memu.sqlite3` (CLI); **required** for host adapters |
| Embedding provider | `MEMU_EMBED_PROVIDER` | `openai` (also: `jina`, `voyage`, `doubao`, `openrouter`); legacy `MEMU_LLM_PROVIDER` still read |
| API key | `MEMU_API_KEY` | the provider's env var, e.g. `OPENAI_API_KEY` |
| Embedding model | `MEMU_EMBED_MODEL` | the provider's default |
| Base URL | `MEMU_BASE_URL` | the provider's default |

### Storage backends

| Provider | DSN | Vector search | Use for |
|---|---|---|---|
| `inmemory` | — | brute-force cosine | tests, throwaway sessions |
| `sqlite` | `sqlite:///path.sqlite3` | brute-force cosine | local/default, single writer |
| `postgres` | `postgresql://...` | pgvector | concurrent access, large stores (`pip install "memu-cli[postgres]"`) |

```python
service = MemoryService(
    database_config={"metadata_store": {"provider": "postgres", "dsn": "postgresql://..."}},
    embedding_profiles={"default": {"provider": "jina"}},
)
```
## License

Apache-2.0
