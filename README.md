![MemU Banner](assets/banner.png)

<div align="center">

# memU

### 24/7 Always-On Proactive Memory for AI Agents

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](readme/README_en.md) | [中文](readme/README_zh.md) | [日本語](readme/README_ja.md) | [한국어](readme/README_ko.md) | [Español](readme/README_es.md) | [Français](readme/README_fr.md)**

</div>

---

memU is a memory framework built for **24/7 proactive agents**.
It is designed for long-running use and greatly **reduces the LLM token cost** of keeping agents always online, making always-on, evolving agents practical in production systems.
memU **continuously captures and understands user intent**. Even without a command, the agent can tell what you are about to do and act on it by itself.

---

## 🤖 [OpenClaw Alternative](https://github.com/NevaMind-AI/memUBot)

<img width="100%" src="https://github.com/NevaMind-AI/MemU/blob/main/assets/memUbot.png" />

**[memU Bot](https://github.com/NevaMind-AI/memUBot)** — Now open source. The enterprise-ready OpenClaw. Your proactive AI assistant that remembers everything.

- **Download-and-use and simple** to get started (one-click install, &lt; 3 min).
- Builds long-term memory to **understand user intent** and act proactively (24/7).
- **Cuts LLM token cost** with smaller context (~1/10 of comparable usage).

Try now: [memu.bot](https://memu.bot) · Source: [memUBot on GitHub](https://github.com/NevaMind-AI/memUBot)

---

## 🗃️ Memory as File System, File System as Memory

memU treats **memory like a file system**—structured, hierarchical, and instantly accessible.

| File System | memU Memory |
|-------------|-------------|
| 📁 Folders | 🏷️ Categories (auto-organized topics) |
| 📄 Files | 🧠 Memory Items (extracted facts, preferences, skills) |
| 🔗 Symlinks | 🔄 Cross-references (related memories linked) |
| 📂 Mount points | 📥 Resources (conversations, documents, images) |

**Why this matters:**
- **Navigate memories** like browsing directories—drill down from broad categories to specific facts
- **Mount new knowledge** instantly—conversations and documents become queryable memory
- **Cross-link everything**—memories reference each other, building a connected knowledge graph
- **Persistent & portable**—export, backup, and transfer memory like files

```
memory/
├── preferences/
│   ├── communication_style.md
│   └── topic_interests.md
├── relationships/
│   ├── contacts/
│   └── interaction_history/
├── knowledge/
│   ├── domain_expertise/
│   └── learned_skills/
└── context/
    ├── recent_conversations/
    └── pending_tasks/
```

Just as a file system turns raw bytes into organized data, memU transforms raw interactions into **structured, searchable, proactive intelligence**.

---

## ⭐️ Star the repository

<img width="100%" src="https://github.com/NevaMind-AI/MemU/blob/main/assets/star.gif" />
If you find memU useful or interesting, a GitHub Star ⭐️ would be greatly appreciated.

---


## ✨ Core Features

| Capability | Description |
|------------|-------------|
| 🤖 **24/7 Proactive Agent** | Always-on memory agent that works continuously in the background |
| 🎯 **User Intention Capture** | Understands and remembers user goals, preferences, and context across sessions automatically |
| 💰 **Cost Efficient** | Reduces long-running token costs by caching insights and avoiding redundant LLM calls |
---

## 🔄 How Proactive Memory Works

```bash
pip install "memu-py[claude]"
# From a source checkout, use: uv sync --extra claude
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
# Optional when using memory.platform instead of memory.local:
export MEMU_API_KEY="..."
cd examples/proactive
python proactive.py
```

---

### Proactive Memory Lifecycle
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         USER QUERY                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                 │                                                           │
                 ▼                                                           ▼
┌────────────────────────────────────────┐         ┌────────────────────────────────────────────────┐
│         🤖 MAIN AGENT                  │         │              🧠 MEMU BOT                        │
│                                        │         │                                                │
│  Handle user queries & execute tasks   │  ◄───►  │  Monitor, memorize & proactive intelligence    │
├────────────────────────────────────────┤         ├────────────────────────────────────────────────┤
│                                        │         │                                                │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  1. RECEIVE USER INPUT           │  │         │  │  1. MONITOR INPUT/OUTPUT                 │  │
│  │     Parse query, understand      │  │   ───►  │  │     Observe agent interactions           │  │
│  │     context and intent           │  │         │  │     Track conversation flow              │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  2. PLAN & EXECUTE               │  │         │  │  2. MEMORIZE & EXTRACT                   │  │
│  │     Break down tasks             │  │   ◄───  │  │     Store insights, facts, preferences   │  │
│  │     Call tools, retrieve data    │  │  inject │  │     Extract skills & knowledge           │  │
│  │     Generate responses           │  │  memory │  │     Update user profile                  │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  3. RESPOND TO USER              │  │         │  │  3. PREDICT USER INTENT                  │  │
│  │     Deliver answer/result        │  │   ───►  │  │     Anticipate next steps                │  │
│  │     Continue conversation        │  │         │  │     Identify upcoming needs              │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  4. LOOP                         │  │         │  │  4. RUN PROACTIVE TASKS                  │  │
│  │     Wait for next user input     │  │   ◄───  │  │     Pre-fetch relevant context           │  │
│  │     or proactive suggestions     │  │  suggest│  │     Prepare recommendations              │  │
│  └──────────────────────────────────┘  │         │  │     Update todolist autonomously         │  │
│                                        │         │  └──────────────────────────────────────────┘  │
└────────────────────────────────────────┘         └────────────────────────────────────────────────┘
                 │                                                           │
                 └───────────────────────────┬───────────────────────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │     CONTINUOUS SYNC LOOP     │
                              │  Agent ◄──► MemU Bot ◄──► DB │
                              └──────────────────────────────┘
```

---

## 🎯 Proactive Use Cases

### 1. **Information Recommendation**
*Agent monitors interests and proactively surfaces relevant content*
```python
# User has been researching AI topics
MemU tracks: reading history, saved articles, search queries

# When new content arrives:
Agent: "I found 3 new papers on RAG optimization that align with
        your recent research on retrieval systems. One author
        (Dr. Chen) you've cited before published yesterday."

# Proactive behaviors:
- Learns topic preferences from browsing patterns
- Tracks author/source credibility preferences
- Filters noise based on engagement history
- Times recommendations for optimal attention
```

### 2. **Email Management**
*Agent learns communication patterns and handles routine correspondence*
```python
# MemU observes email patterns over time:
- Response templates for common scenarios
- Priority contacts and urgent keywords
- Scheduling preferences and availability
- Writing style and tone variations

# Proactive email assistance:
Agent: "You have 12 new emails. I've drafted responses for 3 routine
        requests and flagged 2 urgent items from your priority contacts.
        Should I also reschedule tomorrow's meeting based on the
        conflict John mentioned?"

# Autonomous actions:
✓ Draft context-aware replies
✓ Categorize and prioritize inbox
✓ Detect scheduling conflicts
✓ Summarize long threads with key decisions
```

### 3. **Trading & Financial Monitoring**
*Agent tracks market context and user investment behavior*
```python
# MemU learns trading preferences:
- Risk tolerance from historical decisions
- Preferred sectors and asset classes
- Response patterns to market events
- Portfolio rebalancing triggers

# Proactive alerts:
Agent: "NVDA dropped 5% in after-hours trading. Based on your past
        behavior, you typically buy tech dips above 3%. Your current
        allocation allows for $2,000 additional exposure while
        maintaining your 70/30 equity-bond target."

# Continuous monitoring:
- Track price alerts tied to user-defined thresholds
- Correlate news events with portfolio impact
- Learn from executed vs. ignored recommendations
- Anticipate tax-loss harvesting opportunities
```


...

---

## 🗂️ Hierarchical Memory Architecture

MemU's three-layer system enables both **reactive queries** and **proactive context loading**:

<img width="100%" alt="structure" src="assets/structure.png" />

<img width="100%" alt="memU overall engineering architecture" src="assets/memu-overall-engineering-architecture.png" />

| Layer | Reactive Use | Proactive Use |
|-------|--------------|---------------|
| **Resource** | Direct access to original data | Background monitoring for new patterns |
| **Item** | Targeted fact retrieval | Real-time extraction from ongoing interactions |
| **Category** | Summary-level overview | Automatic context assembly for anticipation |

**Proactive Benefits:**
- **Auto-categorization**: New memories self-organize into topics
- **Pattern Detection**: System identifies recurring themes
- **Context Prediction**: Anticipates what information will be needed next

---

## 🚀 Quick Start

### Option 1: Cloud Version

Experience proactive memory instantly:

👉 **[memu.so](https://memu.so)** - Hosted service with 7×24 continuous learning

For enterprise deployment with custom proactive workflows, contact **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer YOUR_API_KEY` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Register continuous learning task |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Check real-time processing status |
| `POST` | `/api/v3/memory/categories` | List auto-generated categories |
| `POST` | `/api/v3/memory/retrieve` | Query memory (supports proactive context loading) |

📚 **[Full API Documentation](https://memu.pro/docs#cloud-version)**

---

### Option 2: Self-Hosted

#### Installation
```bash
pip install memu-py
```

For local source development, clone this repository and install the editable
workspace:

```bash
make install
```

#### Basic Example

> **Requirements**: Python 3.12+ and an OpenAI API key

Run the getting-started example:

```bash
export OPENAI_API_KEY=your_api_key
python examples/getting_started_robust.py
```

The example initializes `MemoryService`, creates a memory item, and retrieves it
with a natural-language query. See
[`examples/getting_started_robust.py`](examples/getting_started_robust.py) for
the full script.

**Optional PostgreSQL integration check**:

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Run the opt-in PostgreSQL integration test
uv sync --extra postgres
export OPENAI_API_KEY=your_api_key
export MEMU_RUN_POSTGRES_TESTS=1
uv run python -m pytest tests/test_postgres.py
```

These flows demonstrate **proactive memory workflows**:
1. **Continuous Ingestion**: Process multiple files sequentially
2. **Auto-Extraction**: Immediate memory creation
3. **Proactive Retrieval**: Context-aware memory surfacing

See [`tests/test_inmemory.py`](tests/test_inmemory.py), [`tests/test_sqlite.py`](tests/test_sqlite.py),
and [`tests/test_postgres.py`](tests/test_postgres.py) for implementation details. The
in-memory and SQLite live LLM checks are opt-in with `MEMU_RUN_LIVE_LLM_TESTS=1`.

### Context Harness: Folder to Markdown Memory

For local agents that need inspectable context files, memU can compile a folder
of raw data into a Markdown-backed memory repository:

<img width="100%" alt="memU self-evolve engineering architecture" src="assets/memu-self-evolve-architecture.png" />

```text
memory_repo/
  AGENTS.md
  raw_data/
  memory.md
  memory/
  soul.md
  soul/
  skill.md
  skill/
  .memu/
    harness.json
    evolution/
```

Quick CLI workflow:

```bash
memu-harness init memory_repo --source-folder path/to/uploaded-folder
memu-harness doctor memory_repo --json
memu-harness status memory_repo --json
memu-harness refresh memory_repo --query "current agent task"
memu-harness review-evolution memory_repo
memu-harness refresh memory_repo --exclude "node_modules/**" --exclude "*.tmp"
memu-harness promote-skill memory_repo \
  --title "Validate Context Packs" \
  --lesson "Inspect promoted skills before relying on generated context"
memu-harness suggest-skills memory_repo --json
memu-harness context memory_repo --query "current agent task"
memu-harness context memory_repo --query "current agent task" --format summary
memu-harness context memory_repo --query "current agent task" --format messages
memu-harness context memory_repo --bucket-max soul=1000 --bucket-max skill=2000
memu-harness context memory_repo --format system --output context.system.md
```

This flow preserves multimodal files in `raw_data/`, supports sidecar captions,
summaries, notes, and transcripts such as `screenshot.caption.md` or
`report.summary.md`, updates changed files incrementally, and keeps manual skill
notes outside generated blocks. Raw logs, creator feedback, uploads, and new
observations do not edit `memory.md`, `soul.md`, or `skill.md` directly; memU
first turns them into Evolution Instructions, Patch Proposals, and review
decisions, with audit records under `.memu/evolution/`. Exclude noisy files
explicitly with `--exclude` or a `.memuignore` file. `init` also creates
`.memu/harness.json`, where the
repository can persist non-secret defaults such as exclude globs, text evidence
limits, context budgets, and context output format. Both `memu-harness context`
and standalone `memu-context` read those context defaults. Skill traces can be
turned into promotion suggestions with `suggest-skills`; promoted skills are
also stored as stable cards under `skill/promoted/`. New harness repositories
include an `AGENTS.md` bootstrap file so local coding agents can discover the
memory, soul, skill, raw data, and skill-evolution conventions directly from
the repository. Python callers can use `ContextHarness.from_repo("memory_repo")`
to refresh and build context from `memory_repo/raw_data` with the same repo
defaults.

<img width="100%" alt="memU self-evolve algorithm flow" src="assets/memu-self-evolve-algorithm.png" />

Run the no-API-key demo:

```bash
python examples/context_harness_demo.py
```

See [`docs/folder_memory_compiler.md`](docs/folder_memory_compiler.md) for the
full harness API, CLI, watcher, status report, and self-evolving skill workflow.

---

### Custom LLM and Embedding Providers

MemU supports custom LLM and embedding providers beyond OpenAI. Configure them via `llm_profiles`:
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        # Default profile for LLM operations
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "MEMU_QWEN_API_KEY",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk", "httpx", or "lazyllm_backend"
        },
        # Separate profile for embeddings
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "VOYAGE_API_KEY",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... other configuration
)
```

The `lazyllm_backend` adapter is optional. Install it with
`pip install "memu-py[lazyllm]"` or, from a source checkout,
`uv sync --extra lazyllm`.

Optional LazyLLM live check:

```bash
uv sync --extra lazyllm
export MEMU_QWEN_API_KEY=your_api_key
export MEMU_RUN_LAZYLLM_TESTS=1
uv run python -m pytest tests/test_lazyllm.py
```

Retrieve routing can also use distinct profiles: set
`route_intention_llm_profile`, `sufficiency_check_llm_profile`, and
`llm_ranking_llm_profile` in `retrieve_config` to split cheap routing from
heavier ranking or judging models.

---

### OpenRouter Integration

MemU supports [OpenRouter](https://openrouter.ai) as a model provider, giving you access to multiple LLM providers through a single API.

#### Configuration
```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "OPENROUTER_API_KEY",
            "chat_model": "anthropic/claude-3.5-sonnet",  # Any OpenRouter model
            "embed_model": "openai/text-embedding-3-small",  # Embedding model
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
    },
)
```

#### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key from [openrouter.ai/keys](https://openrouter.ai/keys) |

#### Supported Features

| Feature | Status | Notes |
|---------|--------|-------|
| Chat Completions | Supported | Works with any OpenRouter chat model |
| Embeddings | Supported | Use OpenAI embedding models via OpenRouter |
| Vision | Supported | Use vision-capable models (e.g., `openai/gpt-4o`) |

#### Running OpenRouter Tests
```bash
export OPENROUTER_API_KEY=your_api_key
export MEMU_RUN_OPENROUTER_TESTS=1

# Full workflow test (memorize + retrieve)
uv run python -m pytest tests/test_openrouter.py
```

See [`examples/example_4_openrouter_memory.py`](examples/example_4_openrouter_memory.py) for a complete working example.

---

## 📖 Core APIs

<img width="100%" alt="memU overall algorithm flow" src="assets/memu-overall-algorithm-flow.png" />

### `memorize()` - Continuous Learning Pipeline

Processes inputs in real-time and immediately updates memory:

<img width="100%" alt="memorize" src="assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # File path or URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # Optional: scope to a user
)

# Returns immediately with extracted memory:
{
    "resource": {...},      # Stored resource metadata
    "items": [...],         # Extracted memory items (available instantly)
    "categories": [...]     # Auto-updated category structure
}
```

**Proactive Features:**
- Zero-delay processing—memories available immediately
- Automatic categorization without manual tagging
- Cross-reference with existing memories for pattern detection

### `retrieve()` - Dual-Mode Intelligence

MemU supports both **proactive context loading** and **reactive querying**:

<img width="100%" alt="retrieve" src="assets/retrieve.png" />

#### RAG-based Retrieval (`method="rag"`)

Fast **proactive context assembly** using embeddings:

- ✅ **Instant context**: Sub-second memory surfacing
- ✅ **Background monitoring**: Can run continuously without LLM costs
- ✅ **Similarity scoring**: Identifies most relevant memories automatically

#### LLM-based Retrieval (`method="llm"`)

Deep **anticipatory reasoning** for complex contexts:

- ✅ **Intent prediction**: LLM infers what user needs before they ask
- ✅ **Query evolution**: Automatically refines search as context develops
- ✅ **Early termination**: Stops when sufficient context is gathered

#### Comparison

| Aspect | RAG (Fast Context) | LLM (Deep Reasoning) |
|--------|-------------------|---------------------|
| **Speed** | ⚡ Milliseconds | 🐢 Seconds |
| **Cost** | 💰 Embedding only | 💰💰 LLM inference |
| **Proactive use** | Continuous monitoring | Triggered context loading |
| **Best for** | Real-time suggestions | Complex anticipation |

#### Usage
```python
# Proactive retrieval with context history
result = await service.retrieve(
    queries=[
        {"role": "user", "content": "What are their preferences?"},
        {"role": "user", "content": "Tell me about work habits"}
    ],
    where={"user_id": "123"},  # Optional: scope filter
    method="rag",  # or "llm" for deeper reasoning
    ranking="salience",  # or "similarity" for RAG item recall
)

# Returns context-aware results:
{
    "categories": [...],     # Relevant topic areas (auto-prioritized)
    "items": [...],          # Specific memory facts
    "resources": [...],      # Original sources for traceability
    "next_step_query": "..." # Predicted follow-up context
}
```

For a single user query, Python callers can also pass `queries=["What are their preferences?"]`; MemU normalizes it to a user message before retrieval.

**Proactive Filtering**: Use `where` to scope continuous monitoring:
- `where={"user_id": "123"}` - User-specific context
- `where={"agent_id__in": ["1", "2"]}` - Multi-agent coordination
- Omit `where` for global context awareness

`where` keys must match fields on your configured `UserConfig.model`, and values are validated/normalized by that model before querying. Validation is field-level, so partial filters do not need to include every field required by the model. Supported filters are equality (`field`) and membership (`field__in`); unsupported operators are rejected before any backend query runs.

---

## 💡 Proactive Scenarios

### Example 1: Always-Learning Assistant

Continuously learns from every interaction without explicit memory commands:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**Proactive Behavior:**
- Automatically extracts preferences from casual mentions
- Builds relationship models from interaction patterns
- Surfaces relevant context in future conversations
- Adapts communication style based on learned preferences

**Best for:** Personal AI assistants, customer support that remembers, social chatbots

---

### Example 2: Self-Improving Agent

Learns from execution logs and proactively suggests optimizations:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**Proactive Behavior:**
- Monitors agent actions and outcomes continuously
- Identifies patterns in successes and failures
- Auto-generates skill guides from experience
- Proactively suggests strategies for similar future tasks

**Best for:** DevOps automation, agent self-improvement, knowledge capture

---

### Example 3: Multimodal Context Builder

Unifies memory across different input types for comprehensive context:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**Proactive Behavior:**
- Cross-references text, images, and documents automatically
- Builds unified understanding across modalities
- Surfaces visual context when discussing related topics
- Anticipates information needs by combining multiple sources

**Best for:** Documentation systems, learning platforms, research assistants

---

## 📊 Performance

MemU achieves **92.09% average accuracy** on the Locomo benchmark across all reasoning tasks, demonstrating reliable proactive memory operations.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

View detailed experimental data: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Ecosystem

| Repository | Description | Proactive Features |
|------------|-------------|-------------------|
| **[memU](https://github.com/NevaMind-AI/MemU)** | Core proactive memory engine | 7×24 learning pipeline, auto-categorization |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend with continuous sync | Real-time memory updates, webhook triggers |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Visual memory dashboard | Live memory evolution monitoring |

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

## 🤝 How to Contribute

We welcome contributions from the community! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### Getting Started

To start contributing to MemU, you'll need to set up your development environment:

#### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Git

#### Setup Development Environment
```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 2. Install development dependencies
make install
```

The `make install` command will:
- Create a virtual environment using `uv`
- Install all project dependencies
- Set up pre-commit hooks for code quality checks

#### Running Quality Checks

Before submitting your contribution, ensure your code passes all quality checks:
```bash
make check
make test
```

The `make check` command runs:
- **Lock file verification**: Ensures `pyproject.toml` consistency
- **Pre-commit hooks**: Lints and formats code with Ruff
- **Type checking**: Runs `mypy` for static type analysis
- **Dependency analysis**: Uses `deptry` to find obsolete dependencies

The `make test` command runs the pytest suite with coverage enabled.

#### Documentation Site

Preview the documentation locally with MkDocs:

```bash
make docs
```

Build the documentation in strict mode:

```bash
make docs-build
```

### Contributing Guidelines

For detailed contribution guidelines, code standards, and development practices, please see [CONTRIBUTING.md](CONTRIBUTING.md).

**Quick tips:**
- Create a new branch for each feature or bug fix
- Write clear commit messages
- Add tests for new functionality
- Update documentation as needed
- Run `make check` and `make test` before pushing

---

## 📄 License

[Apache License 2.0](LICENSE.txt)

---

## 🌍 Community

- **Support**: [Get help and choose the right channel](SUPPORT.md)
- **Security**: [Report vulnerabilities privately](SECURITY.md)
- **GitHub Issues**: [Report bugs & request features](https://github.com/NevaMind-AI/MemU/issues)
- **GitHub Discussions**: [Ask questions and discuss ideas](https://github.com/NevaMind-AI/MemU/discussions)
- **Discord**: [Join the community](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [Follow @memU_ai](https://x.com/memU_ai)
- **Contact**: contact@nevamind.ai

---

<div align="center">

⭐ **Star us on GitHub** to get notified about new releases!

</div>
