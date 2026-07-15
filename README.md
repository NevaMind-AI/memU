![MemU Banner](assets/banner.png)

<div align="center">

# memU

### Personal memory, stored as files

**Fast retrieval. Higher accuracy. Lower cost.**

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</div>

---

memU is an embedding-only memory store for AI agents. The agent does the reading and writing — memU persists what it produces and hands back compact, ranked context. No LLM call happens inside the service; the only model calls are embeddings.

The whole surface is three operations:

```python
from memu.app import MemoryService

service = MemoryService(database_config={"metadata_store": {"provider": "sqlite", "dsn": "sqlite:///memu.sqlite3"}})

# 1. Persist agent-prepared memory: recall files (memory/skill tracks) + resources
await service.commit_results(
    recall_files=[{"name": "Profile", "track": "memory", "description": "who the user is", "content": "..."}],
    resource=[{"path": "/abs/path/notes.md", "description": "meeting notes"}],
)

# 2. See what is stored, across every track
files = await service.list_all_recall_files()

# 3. Single-shot embedding retrieval over segments / files / resources
context = await service.progressive_retrieve("What should I know about this user's launch preferences?")
```

Or straight from the terminal — no code:

```bash
npx memu-cli list-files
npx memu-cli retrieve "What should I know about this user's launch preferences?"
npx memu-cli commit results.json     # {"recall_files": [...], "resource": [...]}
```

## The memory model

Memory is a set of **recall files** — one Markdown document per topic (`track="memory"`) or per learned skill (`track="skill"`). Each file is sliced into embedded **segments** (memory files: one per content line; skill files: one per skill), and **resources** record the raw sources with an embedded caption.

`progressive_retrieve` embeds the query once and returns three ranked layers:

- `segments` — the matched slices, with scores
- `files` — the documents those segments belong to (usually what you want), each with its linked resource URLs
- `resources` — matching raw sources, for when summaries are not enough

There is no intention routing, sufficiency checking, or summarization — one embedding call in, ranked context out.

## Host adapter: memory for desktop coding agents

`memu-codex` runs memU as a sidecar to Codex-style agents (ADR 0008/0009): a scheduled *bridging* task mines the host's session logs into job files, the agent itself distills them into memory/skill markdown, and `commit` writes the result back through `commit_results`. The *inject* seam patches the host's global instruction file so the agent runs `memu-codex retrieve` (→ `progressive_retrieve`) before answering.

```bash
memu-codex docs install     # agent-facing setup guide
memu-codex doctor           # verify MEMU_* config + store + retrieval
memu-codex prepare          # slice new sessions into self-evolve jobs
memu-codex commit           # submit what the agent produced back into memU
```

## Installation

```bash
pip install memu-py          # library
npx memu-cli --help          # CLI via npm launcher (engine: PyPI package memu-cli)
uvx --from memu-cli memu     # CLI via uv, no install
```

Install only one of `memu-py` / `memu-cli` in a given environment — they ship the same `memu` module.

## Configuration

Every CLI flag has a `MEMU_*` environment variable (also read from `~/.memu/config.env`):

| Setting | Env var | Default |
|---|---|---|
| Store | `MEMU_DB` | `./data/memu.sqlite3` (CLI); required for host adapters |
| Embedding provider | `MEMU_LLM_PROVIDER` | `openai` (also: `jina`, `voyage`, `openrouter`, ...) |
| API key | `MEMU_API_KEY` | the provider's env var, e.g. `OPENAI_API_KEY` |
| Embedding model | `MEMU_EMBED_MODEL` | the provider's default |
| Base URL | `MEMU_BASE_URL` | the provider's default |

Storage backends: `inmemory` (tests), `sqlite` (default, brute-force cosine), `postgres` + pgvector (`pip install "memu-py[postgres]"`).

```python
service = MemoryService(
    database_config={"metadata_store": {"provider": "postgres", "dsn": "postgresql://..."}},
    embedding_profiles={"default": {"provider": "jina"}},
    progressive_retrieve_config={"file": {"top_k": 10, "tracks": ["memory"]}, "resource": {"enabled": False}},
)
```

Scoping: every record carries optional `user_id`/`agent_id` fields; pass `user=` to `commit_results` and `where=` to the read paths to partition one store across users and agents.

## Design docs

The `docs/adr/` directory records the architecture decisions, including the move to tracked workspace memorization (ADR 0006), the segment/file/resource retrieval lines (ADR 0007), and the host-adapter seams (ADR 0008/0009).

## License

Apache-2.0
