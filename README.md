![MemU Banner](assets/banner.png)

<div align="center">

# memU

### Turn Raw Multimodal Data into Agent-Ready Structured Memory

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](readme/README_en.md) | [中文](readme/README_zh.md) | [日本語](readme/README_ja.md) | [한국어](readme/README_ko.md) | [Español](readme/README_es.md) | [Français](readme/README_fr.md)**

</div>

---

memU is a **data-to-memory engine** for AI agents.
It turns raw conversations, documents, images, audio, video, tool logs, and workspace files into an agent memory filesystem that agents can navigate, retrieve from, and use directly.

- **Raw in**: chats, docs, URLs, images, audio/video, logs, and local workspaces
- **Structured out**: `index.md`, `memory.md`, `skill.md`, topic subdocs, typed memory items, relations, and embeddings
- **Agent-ready**: read the compact Markdown entrypoints, drill into subfiles, or load ranked context in one call

---

## 🔄 How It Works

**Raw Multimodal Data → Agent Memory Filesystem → Agent Context**

```
Raw Input                    memU Pipeline                 Filesystem Output
─────────────────────        ─────────────────────         ─────────────────────
chat logs                →   parse + segment           →   memory/preferences.md
documents / URLs         →   extract facts             →   index/api.md
images / video           →   caption + describe        →   memory/visual_context.md
audio                    →   transcribe + summarize    →   memory/events.md
tool logs                →   mine usage patterns       →   skill/tool_usage.md
workspace files          →   categorize + link         →   index/files.md
```

1. **Ingest** — store each source as a `Resource` with its modality and source location
2. **Preprocess** — parse text, caption images/video, transcribe audio, and normalize inputs
3. **Extract** — turn raw content into typed `MemoryItem`s such as profile, event, knowledge, behavior, skill, or tool memories
4. **Organize** — categorize, cross-link, embed, and summarize memories into a browsable structure
5. **Write** — emit compact Markdown entrypoints plus detailed subdocs under `index/`, `memory/`, and `skill/`
6. **Retrieve** — return only the relevant context for the current user, agent, session, or task

---

## 🗂️ Agent Memory Filesystem

memU's primary output is a filesystem-like memory bundle for agents. The top-level files are compact entrypoints. The matching directories contain deeper subdocs that agents can open only when needed.

```txt
.memu/
├── index.md
├── memory.md
├── skill.md
├── index/
│   ├── architecture.md
│   ├── api.md
│   └── files.md
├── memory/
│   ├── decisions.md
│   ├── product_context.md
│   └── open_questions.md
└── skill/
    ├── testing.md
    ├── release.md
    └── coding_style.md
```

| Entry | Role | Subdocs |
|-------|------|---------|
| `index.md` | The map of the workspace: what exists, where it lives, and how to navigate it | `index/` holds deeper maps for architecture, APIs, modules, examples, and files |
| `memory.md` | The compact long-term context an agent should load first | `memory/` holds decisions, constraints, product context, bugs, roadmap, and open questions |
| `skill.md` | The operating manual for how to work in this project | `skill/` holds repo-specific workflows for testing, release, migrations, coding style, and tool use |

This gives agents a stable memory surface: they can start from three small files, then follow paths into focused Markdown documents instead of rereading the raw workspace every time.

---

## 🧩 What memU Builds

The Markdown filesystem is backed by structured memory records:

| Layer | What It Represents | Why Agents Use It |
|-------|--------------------|-------------------|
| **Resource** | Original source artifact: conversation, document, image, video, audio, URL, or file | Trace memory back to its source |
| **MemoryItem** | Atomic structured memory with a type and summary | Inject precise facts, preferences, events, skills, and tool patterns |
| **MemoryCategory** | Auto-generated topic or folder with an evolving summary | Load high-level context before drilling into details |
| **CategoryItem** | Relationship between items and categories | Navigate related memories without reprocessing the source |
| **Embedding** | Vector representation for resources, items, and categories | Retrieve relevant context with low latency |

Example `memorize()` output:

```json
{
  "resource": {
    "id": "res_01",
    "url": "workspace/launch-meeting.mp4",
    "modality": "video",
    "caption": "A product planning discussion about onboarding and launch risks."
  },
  "items": [
    {
      "id": "mem_01",
      "memory_type": "event",
      "summary": "The team decided to simplify onboarding before the next launch review."
    },
    {
      "id": "mem_02",
      "memory_type": "profile",
      "summary": "The user prefers concise implementation plans with explicit verification steps."
    },
    {
      "id": "mem_03",
      "memory_type": "tool",
      "summary": "Use repository-wide search before editing configuration files to avoid missing duplicated settings."
    }
  ],
  "categories": [
    {
      "id": "cat_01",
      "name": "product_goals",
      "summary": "Current launch priorities, onboarding decisions, and unresolved risks."
    }
  ],
  "relations": [
    { "item_id": "mem_01", "category_id": "cat_01" }
  ]
}
```

Then an agent can call `retrieve()` to get a scoped, ranked context payload:

```python
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What context matters for this launch task?"}}],
    where={"user_id": "123"},
    method="rag",
)
```

---

## ⭐️ Star the repository

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

If you find memU useful or interesting, a GitHub Star ⭐️ would be greatly appreciated.

---

## ✨ Core Features

| Capability | Description |
|------------|-------------|
| 🗂️ **Multimodal Ingestion** | Ingest conversations, documents, images, video, audio, URLs, logs, and workspace files |
| 📁 **Memory Filesystem** | Produce `index.md`, `memory.md`, `skill.md`, and focused subdocs under `index/`, `memory/`, and `skill/` |
| 🧠 **Typed Memory Extraction** | Extract profile, event, knowledge, behavior, skill, and tool memories from raw sources |
| 🧭 **Automatic Organization** | Build categories, relations, summaries, and embeddings without manual tagging |
| 🤖 **Agent-Ready Retrieval** | Return scoped, ranked context that can be injected into any agent workflow |
| 🧱 **Pluggable Storage** | Use in-memory, SQLite, or Postgres backends with the same repository contracts |
| 🔀 **Profile-Based LLM Routing** | Route chat, embedding, vision, and transcription work through configurable LLM profiles |

---

## 🎯 Use Cases

### 1. **Conversation Memory**
*Turn chat logs into user preferences, goals, events, and relationship context.*

```python
await service.memorize(
    resource_url="conversations/user_123.json",
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
await service.memorize(resource_url="research-notes.pdf", modality="document")
await service.memorize(resource_url="whiteboard.png", modality="image")
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **Tool and Agent Learning**
*Turn execution traces into tool memories that tell future agents when to use a tool and what mistakes to avoid.*

```python
await service.memorize(resource_url="agent_run.log", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ Architecture

memU's memory model is hierarchical enough for browsing and structured enough for direct retrieval:

<img width="100%" alt="structure" src="assets/structure.png" />

| Layer | Primary Role | Retrieval Role |
|-------|--------------|----------------|
| **Resource** | Preserve source artifacts and captions | Recall original context when item/category summaries are not enough |
| **Item** | Store typed atomic memories | Load precise facts, events, preferences, skills, and tool patterns |
| **Category** | Maintain topic-level summaries | Assemble compact context for broad queries |

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
```bash
pip install -e .
```

> **Requirements**: Python 3.13+ and an OpenAI API key

**Test with in-memory storage:**
```bash
export OPENAI_API_KEY=your_key
cd tests && python test_inmemory.py
```

**Test with PostgreSQL:**
```bash
docker run -d --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

export OPENAI_API_KEY=your_key
cd tests && python test_postgres.py
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
    resource_url="path/to/file.json",    # file path, URL, or directory
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # optional: scope to a user or agent
)
# Returns immediately:
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- Converts raw input into typed memory items
- Categorizes and embeds items without manual tagging
- Preserves source resources and item-category relations

---

### `retrieve()` — Load Agent Context

<img width="100%" alt="retrieve" src="assets/retrieve.png" />

```python
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # scope filter
    method="rag"                # "rag" (fast) or "llm" (deep reasoning)
)
# Returns:
# { "categories": [...], "items": [...], "resources": [...], "next_step_query": "..." }
```

| Method | Speed | Cost | Best For |
|--------|-------|------|----------|
| `rag` | ⚡ ms | embedding only | real-time agent context |
| `llm` | 🐢 seconds | LLM inference | deeper semantic ranking |

---

## 💡 Example Workflows

### Always-Learning Assistant
```bash
export OPENAI_API_KEY=your_key
python examples/example_1_conversation_memory.py
```
Automatically extracts preferences, builds relationship models, and surfaces relevant context in future conversations.

### Self-Improving Agent
```bash
python examples/example_2_skill_extraction.py
```
Monitors agent actions, identifies patterns in successes and failures, auto-generates skill guides from experience.

### Multimodal Context Builder
```bash
python examples/example_3_multimodal_memory.py
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
| **[memU](https://github.com/NevaMind-AI/memU)** | Core data-to-memory engine — ingestion, extraction, retrieval |
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
