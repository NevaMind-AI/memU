![MemU Banner](assets/banner.png)

<div align="center">

# memU

### Personal memory, stored as files

**Across Agents. Fast retrieval. Lower cost.**

[![PyPI version](https://badge.fury.io/py/memu-cli.svg)](https://badge.fury.io/py/memu-cli)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</div>

---

memU is a 500-line memory system for AI agents. Agents write what's worth keeping as Markdown; memU stores it, embeds it, and retrieves ranked context in a single call — embeddings are the only model calls it makes. The entire memory logic lives in [`agentic.py`](src/memu/app/agentic.py) + [`service.py`](src/memu/app/service.py); everything else is pluggable storage and embedding transport.

## Quick start

```python
from memu.app import MemoryService

service = MemoryService(
    database_config={"metadata_store": {"provider": "sqlite", "dsn": "sqlite:///memu.sqlite3"}},
)

# 1. Persist agent-prepared memory: recall files (memory/skill tracks) + resources
await service.commit_results(
    recall_files=[
        {
            "name": "Profile",
            "track": "memory",
            "description": "who the user is",
            "content": "# Profile\n- prefers dark roast coffee\n- ships on Fridays",
        },
        {
            "name": "deploy-checklist",
            "track": "skill",
            "description": "how to deploy this repo",
            "content": "1. run tests\n2. tag\n3. push",
        },
    ],
    resource=[{"path": "/abs/path/notes.md", "description": "meeting notes from the launch review"}],
)

# 2. See what is stored, across every track
files = await service.list_all_recall_files()

# 3. Single-shot embedding retrieval over segments / files / resources
context = await service.progressive_retrieve("What should I know about this user's launch preferences?")
```

Or straight from the terminal — no code:

```bash
export OPENAI_API_KEY=sk-...    # embedding API key — the only model calls memU makes

npx memu-cli commit results.json     # {"recall_files": [...], "resource": [...]}
npx memu-cli list-files
npx memu-cli retrieve "What should I know about this user's launch preferences?"
```

State persists in a local SQLite database (`./data/memu.sqlite3` by default), so commit in one invocation and retrieve in the next.

## How it works

![memU memory system architecture](assets/structure-v2.png)

### The data model

Memory is a set of **recall files** — one Markdown document per topic (`track="memory"`) or per learned skill (`track="skill"`). Committing a file also writes its search index:

| Record | What it is | How it's embedded |
|---|---|---|
| **RecallFile** | The Markdown document itself (`name`, `track`, `description`, `content`) | `name: description`, once at creation |
| **RecallFileSegment** | Searchable slices of a file | memory track: one per content line (headings skipped); skill track: one `name: description` segment per skill |
| **Resource** | A raw source on disk (`url`, `caption`) | its one-line caption |

Segments are reconciled on every commit: lines that disappeared are deleted, only genuinely new lines are embedded, unchanged lines keep their vectors — so re-committing a lightly edited file is nearly free.

### Retrieval

`progressive_retrieve(query)` embeds the query **once** and returns three ranked layers:

- `segments` — the matched slices, narrowest and usually most on-point, each with a `score`
- `files` — the documents those segments belong to (usually what you want), each scored by its best segment and carrying its linked `resource_urls`
- `resources` — matching raw sources, for when summaries are not enough

There is no intention routing, sufficiency checking, or summarization — one embedding call in, ranked context out.

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
| **any other agent** | `memu-agent` | found by `memu-agent detect` (JSONL dialect sniffed) | found by `detect` (AGENTS.md / CLAUDE.md / SOUL.md / …) |

For agents without a dedicated binary, `memu-agent detect` probes the machine and reports per agent whether **memorization** works (a recognizable session log exists) and whether **retrieval** works (an instruction file exists to patch) — then the same verbs run against what it found.

All hosts share one store and one embedding space via `~/.memu/config.env` — what one host's sessions taught memU, another host retrieves.

**Installation is agent-driven.** The install guide is written for the agent, not for you — install the package, then hand the guide to your agent and let it do the rest (configure the store, register the scheduled bridging task, patch the instruction file — each step ends with a verify gate):

```bash
pip install memu-cli    # puts memu + the host binaries on PATH
```

Then tell your agent (swap in your host's binary):

> Run `memu-codex docs install`, read the guide it prints, and follow it to install memU.

Afterwards `<binary> doctor` proves the whole loop resolves: config, store, and a live retrieval.

Adding another host means implementing one `TranscriptSource` (where its session logs live, how its records are shaped) plus a `HostSpec`-sized CLI — the pipeline, verbs, and instruction text are shared (ADR 0010).

## Installation

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

### Multi-tenancy

Every record carries optional scope fields (`user_id`, `agent_id` by default). Pass `user=` on writes and `where=` on reads to partition one store:

```python
await service.commit_results(recall_files=[...], user={"user_id": "alice"})
await service.progressive_retrieve("launch preferences", where={"user_id": "alice"})
```

Need different scope fields? Supply your own model — filters are validated against it, unknown fields raise:

```python
from pydantic import BaseModel

class TeamScope(BaseModel):
    team_id: str | None = None
    user_id: str | None = None

service = MemoryService(user_config={"model": TeamScope})
```

## Development

```bash
make install     # uv sync + pre-commit hooks
make test        # pytest with coverage
make check       # lock check, pre-commit, mypy, deptry
```

Architecture decisions live in [`docs/adr/`](docs/adr/) — notably tracked workspace memorization (ADR 0006), the segment/file/resource retrieval lines (ADR 0007), and the host-adapter seams (ADR 0008/0009).

## License

Apache-2.0
