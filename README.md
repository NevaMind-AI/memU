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

**[English](readme/README_en.md) | [中文](readme/README_zh.md) | [日本語](readme/README_ja.md) | [한국어](readme/README_ko.md) | [Español](readme/README_es.md) | [Français](readme/README_fr.md)**

</div>

---

> [!WARNING]
> 🚧 **Under heavy construction** — memU is undergoing a major rework. APIs, CLI commands, and docs may change without notice. Things are expected to stabilize around **July 15, 2026**.

> 🤖 **Agents**: read [`.claude/skills/memu/SKILL.md`](.claude/skills/memu/SKILL.md) and you can `memorize-workspace` and `retrieve-workspace` right away.

memU compiles conversations, documents, code, images, audio, video, URLs, and tool traces into human-readable Markdown files (`INDEX.md`, `MEMORY.md`, `SKILL.md`). Agents traverse the tree and load only what the moment needs — instead of rescanning everything or stuffing long histories into every prompt.


```python
await service.memorize_workspace(folder="./workspace")

context = await service.retrieve_workspace("What should I know about this user's launch preferences?")
```

Or straight from the terminal — no code:

```bash
npx memu-cli memorize-workspace ./workspace
npx memu-cli retrieve-workspace "What should I know about this user's launch preferences?"
```

That's it. Instead of one giant prompt about a person or their workspace, your agent gets three durable layers it can traverse:

```txt
workspace/
├── INDEX.md              ← Index: a map of everything — raw sources and summaries
├── MEMORY.md             ← Memory: an overview that links into memory/
├── SKILL.md              ← Skill: an overview that links into skill/
├── resource/             ← the raw source files, copied verbatim
├── memory/
│   └── <topic>.md        ← one memory file per topic: facts, preferences, goals, events
└── skill/
    └── <name>.md         ← one skill file per learned pattern, workflow, or mistake to avoid
```

- **Index (`INDEX.md`)** — a map of your memories: what exists, where it came from, and where to look first
- **Memory (`MEMORY.md`)** — personal facts, preferences, goals, events, and decisions extracted from source data
- **Skill (`SKILL.md`)** — **auto-extracted from agent traces and refined on every workspace sync** so the agent improves at recurring tasks

When you sync a folder with `memorize_workspace`, the top-level directory decides the treatment: files under `chat/` become memory, files under `agent/` become skills, and everything else is indexed as workspace context.

Three things make it different from stuffing everything into the prompt:

- **Fast retrieval** — walk to the right folder and rank the right files instead of scanning everything every time.
- **Higher accuracy** — scope by user, task, or session, and trace every item back to the exact conversation, document, image, or log it came from.
- **Lower cost** — retrieve compact, scoped context instead of reinjecting long histories, documents, logs, and media-derived text into every prompt.
- **Yours to inspect** — a human-readable file tree you can audit, edit, scope, and route through your own storage (`inmemory`, `sqlite`, `postgres`) and LLM providers.


---

## ⭐️ Star the repository

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

If you find memU useful or interesting, a GitHub Star ⭐️ would be greatly appreciated.

---

## ✨ Core Features

| Capability | Description |
|------------|-------------|
| 🗂️ **Multimodal Ingestion** | Write conversations, documents, images, video, audio, URLs, logs, and local files into memory |
| 📁 **Compiled Memory Workspace** | Persist the Index, Skill, and Memory layers — folders (categories), files (items), source artifacts, links, summaries, and embeddings |
| 🧠 **Typed Memory Extraction** | Extract profile, event, knowledge, behavior, skill, and tool memories from raw sources |
| 🛠️ **Self-Evolving Skills** | Auto-extract reusable tool patterns and workflows from agent traces, then merge and refine them on every workspace sync instead of relearning |
| 🧭 **Self-Organizing Folders** | Auto-build categories, links, summaries, and embeddings without manual tagging |
| 🤖 **Agent-Ready Retrieval** | LLM-free `retrieve_workspace()` ranks memory segments, files, and source resources directly |
| 🔄 **Incremental Workspace Sync** | `memorize_workspace()` diffs a folder against a manifest — only changed files are (re)processed, deletions cascade |
| 🧱 **Pluggable Storage** | Use in-memory, SQLite, or Postgres backends with the same repository contracts |
| 🔀 **Profile-Based LLM Routing** | Route chat, embedding, vision, and transcription work through configurable LLM profiles |
| ⌨️ **CLI** | `memu` command (pip) and `npx memu-cli` (npm) — memorize and retrieve from the terminal or CI |

---

## 🎯 Use Cases

Every use case is the same loop: drop sources into a folder, sync it with `memorize_workspace()`, then ask with `retrieve_workspace()`. The sync is incremental (only changed files are reprocessed), and the top-level directory decides the treatment — `chat/` → memory topics, `agent/` → skills, everything else → indexed context.

### 1. **Personal Memory**
*Turn chat logs into user preferences, goals, events, decisions, and relationship context.*

```python
# workspace/chat/*.json — conversation logs become memory topic files
await service.memorize_workspace(folder="./workspace")

context = await service.retrieve_workspace("What should I remember about this user?")
```

### 2. **Workspace Context for Coding Agents**
*Convert docs, PR notes, logs, and design decisions into reusable project memory.*

```python
# docs, notes, and logs anywhere in the folder are captioned and indexed
await service.memorize_workspace(folder="./workspace")

context = await service.retrieve_workspace("How should I structure this module?")
```

### 3. **Multimodal Knowledge Layer**
*Extract searchable facts from documents, screenshots, images, videos, and audio notes.*

```python
# modality is inferred per file: .pdf/.docx/.pptx/.xlsx/.html (via MarkItDown —
# pip install 'memu-py[document]'), .png/.jpg, .mp3/.wav, .mp4/.mov, ...
await service.memorize_workspace(folder="./workspace")

context = await service.retrieve_workspace("What matters for the next research plan?")
```

### 4. **Tool and Agent Learning**
*Turn execution traces into skills that tell future agents what worked and what to avoid.*

```python
# workspace/agent/*.txt — execution traces are distilled into skill files
await service.memorize_workspace(folder="./workspace")

context = await service.retrieve_workspace("Which tools worked for config editing?")
```

---

## 🗂️ Architecture

The compiled workspace is easiest to read as two directions:

- `memorize_workspace()` writes a folder into durable memory files, skill files, resource records, segments, links, and embeddings.
- `retrieve_workspace()` reads those layers directly, ranking segments first and rolling results up to the files and resources an agent should load.

Memory is stored in three representation layers:

| Layer | What it holds | Retrieval Role |
|-------|---------------|----------------|
| **File** (`RecallFile`) | A synthesized memory topic or skill document | The unit returned to the agent — hit segments roll up to their file |
| **Segment** | Fine slices of a file (paragraph lines, skill descriptions) | The embedded search unit — queries rank segments first |
| **Resource** | The raw source artifact with its caption | Recall original context when synthesized summaries are not enough |

`retrieve_workspace()` embeds the query once, ranks segments and resources by similarity, and returns compact context with zero chat-LLM calls.

See [docs/architecture.md](docs/architecture.md) for the runtime view of `MemoryService`, workflow pipelines, storage backends, and LLM routing, and [docs/adr/](docs/adr/README.md) for the decision records behind the layered design.

---

## 🧰 Agent Skills

The repo ships one [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) — [`.claude/skills/memu/SKILL.md`](.claude/skills/memu/SKILL.md) — that gives Claude Code (and any skills-compatible agent) the workspace pair. The agent decides when to use each direction:

- **memorize** (`memu memorize-workspace`) — "remember this", "sync this folder into memory", finishing work worth persisting
- **retrieve** (`memu retrieve-workspace`) — "what do we know about…", starting a task with likely prior context

It works out of the box inside this repo. To use it in your own project, copy the skill folder into that project's `.claude/skills/` (or `~/.claude/skills/` to enable it everywhere):

```bash
cp -r .claude/skills/memu /path/to/your-project/.claude/skills/
```

The skill locates the CLI automatically (`memu`, `uvx --from memu-py memu`, or `npx memu-cli`) and keeps state in the project-local `./data/memu.sqlite3`, so what one session memorizes the next can retrieve. For LangGraph agents, see the [LangGraph integration](docs/langgraph_integration.md) instead.

---

## 🚀 Quick Start

### Option 1: Cloud Version

👉 **[memu.so](https://memu.so)** — Hosted API for managed ingestion, structured memory, and retrieval

For enterprise deployment: **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer <token>` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Ingest raw data and build structured memory |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Check processing status |
| `POST` | `/api/v3/memory/categories` | List auto-generated categories |
| `POST` | `/api/v3/memory/retrieve` | Query memory for agent context |

📚 **[Full API Documentation](https://memu.pro/docs#cloud-version)**

---

### Option 2: Self-Hosted

#### Installation

From a clone of this repository:

```bash
uv sync
# or, for the full development setup:
make install
```

To install the published package instead:

```bash
pip install memu-py        # library + `memu` CLI
# or from the JS ecosystem (thin launcher over memu-py, uses uvx/pipx automatically):
npx memu-cli --help
```

> **Requirements**: Python 3.13+. The default examples use OpenAI, so set `OPENAI_API_KEY` or pass another provider through `llm_profiles`.

#### Command line

The `memu` command wraps the same service the library exposes. State persists in a local SQLite database (`./data/memu.sqlite3` by default), so memorize in one invocation and retrieve in the next:

```bash
export OPENAI_API_KEY=your_key

memu memorize-workspace ./workspace             # diff-sync a folder (alias: memu sync)
memu retrieve-workspace "deploy checklist"      # LLM-free embedding retrieval (alias: memu search)
memu export                                     # rebuild the INDEX.md/MEMORY.md/SKILL.md tree
```

Every flag has a `MEMU_*` environment variable (`--provider`/`MEMU_LLM_PROVIDER`, `--model`/`MEMU_CHAT_MODEL`, `--db`/`MEMU_DB`, ...) — run `memu <command> --help` for the full list. `--db` accepts a SQLite path, a `postgres://` DSN, or `:memory:`.

**Run an in-memory smoke script:**
```bash
export OPENAI_API_KEY=your_key
cd tests
uv run python test_inmemory.py
```

**Run with PostgreSQL + pgvector:**
```bash
uv sync --extra postgres
docker run -d --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

export OPENAI_API_KEY=your_key
export POSTGRES_DSN=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/memu
cd tests
uv run python test_postgres.py
```

---

### Custom LLM and Embedding Providers

```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"
        },
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
)
```

---

### OpenRouter Integration

```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_key",
            "chat_model": "anthropic/claude-3.5-sonnet",
            "embed_model": "openai/text-embedding-3-small",
        },
    },
    database_config={"metadata_store": {"provider": "inmemory"}},
)
```

---

## 📖 Core APIs

The primary API pair is `memorize_workspace()` / `retrieve_workspace()` — folder in, ranked context out.

### `memorize_workspace()` — Sync a Folder

<img width="100%" alt="memorize_workspace" src="assets/memorize.png" />

```python
result = await service.memorize_workspace(
    folder="./workspace",              # scanned recursively; modality inferred per file
    user={"user_id": "123"},           # optional scope
)
# Returns the diff plus what changed:
# { "added": [...], "modified": [...], "deleted": [...],
#   "resources": [...], "entries": [...], "files": [...] }
```

- Diffs the folder against a sidecar `.memu_manifest.json` — only added/modified files are processed, memory from deleted files is cascade-removed
- Routes by top-level directory: `chat/` → memory files, `agent/` → skill files, everything else → indexed workspace context
- Rebuilds the markdown memory tree (`INDEX.md` / `MEMORY.md` / `SKILL.md`) when `memory_files_config.enabled=True`

---

### `retrieve_workspace()` — Fast, LLM-Free Retrieval

<img width="100%" alt="retrieve_workspace" src="assets/retrieve.png" />

```python
result = await service.retrieve_workspace(
    "deploy checklist",
    where={"user_id": "123"},
)
# Returns:
# { "segments": [...],    # embedded slices ranked by similarity
#   "files": [...],       # the memory/skill files those segments roll up to
#   "resources": [...] }  # workspace resources ranked by similarity
```

The query is embedded once and ranked by vector similarity — no intention routing, no query rewriting, no sufficiency checks, zero LLM calls. Use it for high-frequency lookups where latency and cost matter more than deep reasoning.

---

## 💡 Example Workflows

### Always-Learning Assistant
```bash
export OPENAI_API_KEY=your_key
uv run python examples/example_1_conversation_memory.py
```
Automatically extracts preferences, builds relationship models, and surfaces relevant context in future conversations.

### Self-Improving Agent
```bash
uv run python examples/example_2_skill_extraction.py
```
Monitors agent actions, identifies patterns in successes and failures, auto-generates skill guides from experience.

### Multimodal Context Builder
```bash
uv run python examples/example_3_multimodal_memory.py
```
Cross-references text, images, and documents automatically into a unified memory layer.

---

## 📊 Performance

memU achieves **92.09% average accuracy** on the Locomo benchmark across all reasoning tasks.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

View detailed results: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Ecosystem

| Repository | Description |
|------------|-------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | Personal memory as files — fast retrieval, higher accuracy, lower cost |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend with real-time sync and webhook triggers |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Visual dashboard for browsing and monitoring memory |

**Quick Links:**
- 🚀 [Try MemU Cloud](https://app.memu.so/quick-start)
- 📚 [API Documentation](https://memu.pro/docs)
- 💬 [Discord Community](https://discord.com/invite/hQZntfGsbJ)

---

## 🤝 Partners

<div align="center">

<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://openagents.org"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Milvus" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="Jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="Buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="Bytebase" height="40" style="margin: 10px;"></a>
<a href="https://github.com/LazyAGI/LazyLLM"><img src="assets/partners/LazyLLM.png" alt="LazyLLM" height="40" style="margin: 10px;"></a>
<a href="https://clawdchat.ai/"><img src="assets/partners/Clawdchat.png" alt="Clawdchat" height="40" style="margin: 10px;"></a>

</div>

---

## 🤝 Contributing

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# Install dev dependencies
make install

# Run quality checks before submitting
make check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

**Prerequisites:** Python 3.13+, [uv](https://github.com/astral-sh/uv), Git

---

## 📄 License

[Apache License 2.0](LICENSE.txt)

---

## 🌍 Community

- **GitHub Issues**: [Report bugs & request features](https://github.com/NevaMind-AI/memU/issues)
- **Discord**: [Join the community](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [Follow @memU_ai](https://x.com/memU_ai)
- **Contact**: info@nevamind.ai

---

<div align="center">

⭐ **Star us on GitHub** to get notified about new releases!

</div>
