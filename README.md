![MemU Banner](assets/banner.png)

<div align="center">

# memU

### Your personal file-based memory

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](readme/README_en.md) | [中文](readme/README_zh.md) | [日本語](readme/README_ja.md) | [한국어](readme/README_ko.md) | [Español](readme/README_es.md) | [Français](readme/README_fr.md)**

</div>

---

**Personal memory, stored as files.** memU turns the data around a user — conversations, documents, code, images, audio, video, URLs, and tool traces — into a tree of human-readable Markdown files your agent can open and traverse. No opaque vector blob, no giant prompt: just `INDEX.md`, `MEMORY.md`, and `SKILL.md` the agent navigates before it acts.


```python
await service.memorize(resource_url="workspace/meeting-notes.md", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What should I know about this user's launch preferences?"}}],
    where={"user_id": "123"},
)
```

That's it. Instead of one giant prompt about a person or their workspace, your agent gets three durable layers it can traverse:

```txt
workspace/
├── INDEX.md              ← Index: a map of everything — categories, files, and summaries
├── MEMORY.md             ← Memory: profile, preferences, goals, facts, and key events
└── skill/
    ├── {skill_name}/
    │   └── SKILL.md       ← Skill: a learned tool pattern, workflow, or mistake to avoid
    └── {another_skill}/
        └── SKILL.md
```

- **Index (`INDEX.md`)** — a map of the user's memory workspace: what exists, where it came from, and where to look first
- **Memory (`MEMORY.md`)** — personal facts, preferences, goals, events, and decisions extracted from source data
- **Skill (`SKILL.md`)** — **auto-extracted from tool traces and refined on every `memorize()`** so the agent improves at recurring tasks

Three things make it different from stuffing everything about a person into the prompt:

- **Faster traversal** — walk to the right folder and rank the right files instead of scanning the whole workspace every time.
- **Lower cost** — retrieve compact, scoped memory instead of reinjecting long histories, documents, logs, and media-derived text into every prompt.
- **Higher accuracy** — scope by user, task, or session, and trace every item back to the exact conversation, document, image, or log it came from.
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
| 🛠️ **Self-Evolving Skills** | Auto-extract reusable tool patterns and workflows from tool traces, then merge and refine them on every `memorize()` instead of relearning |
| 🧭 **Self-Organizing Folders** | Auto-build categories, links, summaries, and embeddings without manual tagging |
| 🤖 **Agent-Ready Retrieval** | Read scoped, ranked context that can be injected into any agent workflow |
| 🧱 **Pluggable Storage** | Use in-memory, SQLite, or Postgres backends with the same repository contracts |
| 🔀 **Profile-Based LLM Routing** | Route chat, embedding, vision, and transcription work through configurable LLM profiles |

---

## 🎯 Use Cases

### 1. **Personal Memory**
*Turn chat logs and workspace notes into user preferences, goals, events, decisions, and relationship context.*

```python
await service.memorize(
    resource_url="examples/resources/conversations/conv1.json",
    modality="conversation",
    user={"user_id": "123"},
)

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What should I remember about this user?"}}],
    where={"user_id": "123"},
)
```

### 2. **Workspace Context for Coding Agents**
*Convert docs, PR notes, logs, and design decisions into reusable project memory.*

```python
await service.memorize(resource_url="docs/architecture.md", modality="document")
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "How should I structure this module?"}}],
)
```

### 3. **Multimodal Knowledge Layer**
*Extract searchable facts from documents, screenshots, images, videos, and audio notes.*

```python
await service.memorize(resource_url="examples/resources/docs/doc1.txt", modality="document")
# Rich documents (PDF/Word/PowerPoint/Excel/HTML) are converted to Markdown via
# MarkItDown — install the extra with: pip install 'memu-py[document]'
await service.memorize(resource_url="reports/q3-summary.pdf", modality="document")
await service.memorize(resource_url="examples/resources/images/image1.png", modality="image")
# Audio is supported for your own .mp3/.wav/.m4a files.
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **Tool and Agent Learning**
*Turn execution traces into tool memories that tell future agents when to use a tool and what mistakes to avoid.*

```python
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ Architecture

The compiled workspace is hierarchical enough for browsing and structured enough for direct retrieval:

<img width="100%" alt="structure" src="assets/structure.png" />

| Layer | Primary Role | Retrieval Role |
|-------|--------------|----------------|
| **Category (folder)** | Maintain topic-level summaries | Assemble compact context for broad queries |
| **Item (file)** | Store typed atomic memories | Load precise facts, events, preferences, skills, and tool patterns |
| **Resource (source)** | Preserve source artifacts and captions | Recall original context when item/category summaries are not enough |

See [docs/architecture.md](docs/architecture.md) for the runtime view of `MemoryService`, workflow pipelines, storage backends, and LLM routing.

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
pip install memu-py
```

> **Requirements**: Python 3.13+. The default examples use OpenAI, so set `OPENAI_API_KEY` or pass another provider through `llm_profiles`.

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
from memu import MemUService

service = MemUService(
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

### `memorize()` — Structure Raw Data

<img width="100%" alt="memorize" src="assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",    # local file path or HTTP URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # optional: scope to a user or agent
)
# Returns after processing completes:
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- Converts raw input into typed memory items
- Categorizes and embeds items without manual tagging
- Preserves source resources and item-category relations

---

### `retrieve()` — Load Agent Context

<img width="100%" alt="retrieve" src="assets/retrieve.png" />

```python
# The retrieval strategy is set once on the service via retrieve_config:
#   MemoryService(retrieve_config={"method": "rag"})   # vector-first recall
#   MemoryService(retrieve_config={"method": "llm"})   # LLM-ranked recall
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # scope filter
)
# Returns:
# {
#   "needs_retrieval": true,
#   "original_query": "...",
#   "rewritten_query": "...",
#   "next_step_query": "...",
#   "categories": [...],
#   "items": [...],
#   "resources": [...]
# }
```

| `retrieve_config.method` | Behavior | Cost | Best For |
|--------------------------|----------|------|----------|
| `rag` | Vector-first category/item/resource recall, with optional LLM routing and sufficiency checks enabled by default | Embeddings plus LLM calls unless `route_intention` and `sufficiency_check` are disabled | Fast scoped recall with controllable reasoning |
| `llm` | LLM-ranked category/item/resource recall | LLM ranking at each tier | Deeper semantic ranking |

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
| **[memU](https://github.com/NevaMind-AI/memU)** | Personal information memory runtime — workspace ingestion, extraction, retrieval |
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
