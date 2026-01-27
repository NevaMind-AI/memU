![MemU Banner](assets/banner.png)

<div align="center">

# MemU

### Always-On Proactive Memory for AI Agents

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](readme/README_en.md) | [中文](readme/README_zh.md) | [日本語](readme/README_ja.md) | [한국어](readme/README_ko.md) | [Español](readme/README_es.md) | [Français](readme/README_fr.md)**

</div>

---

MemU is a **7×24 proactive memory framework** that continuously learns, anticipates, and adapts. It transforms passive LLM backends into intelligent agents with **always-on memory** that proactively surfaces insights, predicts needs, and evolves context without explicit queries.

---

## ⭐️ Star the repository

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
If you find memU useful or interesting, a GitHub Star ⭐️ would be greatly appreciated.

---


## ✨ Core Capabilities

| Capability | Description |
|------------|-------------|
| 🔄 **Continuous Learning** | 7×24 memory extraction from every interaction—conversations, documents, actions |
| 🎯 **Proactive Retrieval** | Anticipates information needs before being asked, surfaces relevant context automatically |
| 🧠 **Context Evolution** | Memory structure adapts in real-time based on usage patterns and emerging topics |
| 🔍 **Dual Intelligence** | Fast embedding-based recall + deep LLM reasoning for comprehensive understanding |
| 🎨 **Multimodal Awareness** | Unified memory across text, images, audio, video—remembers what it sees and hears |

---

## 🔄 How Proactive Memory Works

Unlike traditional retrieval systems that wait for queries, MemU operates in **continuous mode**:

### Passive vs. Proactive Memory

| Traditional RAG | MemU Proactive Memory |
|-----------------|----------------------|
| ❌ Waits for explicit queries | ✅ Monitors context continuously |
| ❌ Reactive information retrieval | ✅ Anticipates information needs |
| ❌ Static knowledge base | ✅ Self-evolving memory structure |
| ❌ One-time processing | ✅ Always-on learning pipeline |

### Proactive Memory Lifecycle
```
┌─────────────────────────────────────────────────┐
│  1. CONTINUOUS INGESTION                        │
│  └─ Every conversation, document, action        │
│     automatically processed 7×24                │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  2. REAL-TIME EXTRACTION                        │
│  └─ Immediate memory item creation              │
│     No batch delays, instant availability       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  3. PROACTIVE STRUCTURING                       │
│  └─ Auto-categorization into evolving topics    │
│     Hierarchical organization adapts to usage   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  4. ANTICIPATORY RETRIEVAL                      │
│  └─ Surfaces relevant memory without prompting  │
│     Context-aware suggestions and insights      │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Proactive Use Cases

### 1. **Contextual Assistance**
*Agent monitors conversation context and proactively surfaces relevant memories*
```python
# User starts discussing a topic
User: "I'm thinking about that project..."

# MemU automatically retrieves without explicit query:
- Previous project discussions
- Related preferences and constraints
- Past decisions and their outcomes
- Relevant documents and resources

Agent: "Based on your previous work on the dashboard redesign,
        I noticed you preferred Material UI components..."
```

### 2. **Predictive Preparation**
*Agent anticipates upcoming needs based on patterns*
```python
# Morning routine detection
User logs in at 9 AM (usual time)

# MemU proactively surfaces:
- Daily standup talking points
- Overnight notifications summary
- Priority tasks based on past behavior
- Relevant context from yesterday's work

Agent: "Good morning! Here's what's relevant today..."
```

### 3. **Autonomous Memory Management**
*System self-organizes without manual intervention*
```python
# As interactions accumulate:
✓ Automatically creates new categories for emerging topics
✓ Consolidates related memories across modalities
✓ Identifies patterns and extracts higher-level insights
✓ Prunes outdated information while preserving history

# Result: Always-optimized memory structure
```

---

## 🗂️ Hierarchical Memory Architecture

MemU's three-layer system enables both **reactive queries** and **proactive context loading**:

<img width="100%" alt="structure" src="assets/structure.png" />

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
pip install -e .
```

#### Basic Example

> **Requirements**: Python 3.13+ and an OpenAI API key

**Test Continuous Learning** (in-memory):
```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**Test with Persistent Storage** (PostgreSQL):
```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Run continuous learning test
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

Both examples demonstrate **proactive memory workflows**:
1. **Continuous Ingestion**: Process multiple files sequentially
2. **Auto-Extraction**: Immediate memory creation
3. **Proactive Retrieval**: Context-aware memory surfacing

See [`tests/test_inmemory.py`](tests/test_inmemory.py) and [`tests/test_postgres.py`](tests/test_postgres.py) for implementation details.

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
            "api_key": "your_api_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk" or "http"
        },
        # Separate profile for embeddings
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_voyage_api_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... other configuration
)
```

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
            "api_key": "your_openrouter_api_key",
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

# Full workflow test (memorize + retrieve)
python tests/test_openrouter.py

# Embedding-specific tests
python tests/test_openrouter_embedding.py

# Vision-specific tests
python tests/test_openrouter_vision.py
```

See [`examples/example_4_openrouter_memory.py`](examples/example_4_openrouter_memory.py) for a complete working example.

---

## 📖 Core APIs

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
        {"role": "user", "content": {"text": "What are their preferences?"}},
        {"role": "user", "content": {"text": "Tell me about work habits"}}
    ],
    where={"user_id": "123"},  # Optional: scope filter
    method="rag"  # or "llm" for deeper reasoning
)

# Returns context-aware results:
{
    "categories": [...],     # Relevant topic areas (auto-prioritized)
    "items": [...],          # Specific memory facts
    "resources": [...],      # Original sources for traceability
    "next_step_query": "..." # Predicted follow-up context
}
```

**Proactive Filtering**: Use `where` to scope continuous monitoring:
- `where={"user_id": "123"}` - User-specific context
- `where={"agent_id__in": ["1", "2"]}` - Multi-agent coordination
- Omit `where` for global context awareness

> 📚 **For complete API documentation**, see [SERVICE_API.md](docs/SERVICE_API.md) - includes proactive workflow patterns, pipeline configuration, and real-time update handling.

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
| **[memU](https://github.com/NevaMind-AI/memU)** | Core proactive memory engine | 7×24 learning pipeline, auto-categorization |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend with continuous sync | Real-time memory updates, webhook triggers |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Visual memory dashboard | Live memory evolution monitoring |

**Quick Links:**
- 🚀 [Try MemU Cloud](https://app.memu.so/quick-start)
- 📚 [API Documentation](https://memu.pro/docs)
- 💬 [Discord Community](https://discord.gg/memu)

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

</div>

---

## 🤝 How to Contribute

We welcome contributions from the community! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### Getting Started

To start contributing to MemU, you'll need to set up your development environment:

#### Prerequisites
- Python 3.13+
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
```

The `make check` command runs:
- **Lock file verification**: Ensures `pyproject.toml` consistency
- **Pre-commit hooks**: Lints code with Ruff, formats with Black
- **Type checking**: Runs `mypy` for static type analysis
- **Dependency analysis**: Uses `deptry` to find obsolete dependencies

### Contributing Guidelines

For detailed contribution guidelines, code standards, and development practices, please see [CONTRIBUTING.md](CONTRIBUTING.md).

**Quick tips:**
- Create a new branch for each feature or bug fix
- Write clear commit messages
- Add tests for new functionality
- Update documentation as needed
- Run `make check` before pushing

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
