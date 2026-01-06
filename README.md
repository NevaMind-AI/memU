![MemU Banner](assets/banner.png)

<div align="center">

# MemU

### A Future-Oriented Agentic Memory System

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

</div>

---

MemU is an agentic memory framework for LLM and AI agent backends. It receives **multimodal inputs** (conversations, documents, images), extracts them into structured memory, and organizes them into a **hierarchical file system** that supports both **embedding-based (RAG)** and **non-embedding (LLM)** retrieval.

---

MemU is collaborating with four open-source projects to launch the 2026 New Year Challenge. 🎉Between January 8–18, contributors can submit PRs to memU and earn cash rewards, community recognition, and platform credits. 🎁[Learn more & get involved](https://discord.gg/KaWy6SBAsx)

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🗂️ **Hierarchical File System** | Three-layer architecture: Resource → Item → Category with full traceability |
| 🔍 **Dual Retrieval Methods** | RAG (embedding-based) for speed, LLM (non-embedding) for deep semantic understanding |
| 🎨 **Multimodal Support** | Process conversations, documents, images, audio, and video |
| 🔄 **Self-Evolving Memory** | Memory structure adapts and improves based on usage patterns |

---

## 🗂️ Hierarchical File System

MemU organizes memory using a **three-layer architecture** inspired by hierarchical storage systems:

<img width="100%" alt="structure" src="assets/structure.png" />

| Layer | Description | Examples |
|-------|-------------|----------|
| **Resource** | Raw multimodal data warehouse | JSON conversations, text documents, images, videos |
| **Item** | Discrete extracted memory units | Individual preferences, skills, opinions, habits |
| **Category** | Aggregated textual memory with summaries | `preferences.md`, `work_life.md`, `relationships.md` |

**Key Benefits:**
- **Full Traceability**: Track from raw data → items → categories and back
- **Progressive Summarization**: Each layer provides increasingly abstracted views
- **Flexible Organization**: Categories evolve based on content patterns

---

## 🎨 Multimodal Support

MemU processes diverse content types into unified memory:

| Modality | Input | Processing |
|----------|-------|------------|
| `conversation` | JSON chat logs | Extract preferences, opinions, habits, relationships |
| `document` | Text files (.txt, .md) | Extract knowledge, skills, facts |
| `image` | PNG, JPG, etc. | Vision model extracts visual concepts and descriptions |
| `video` | Video files | Frame extraction + vision analysis |
| `audio` | Audio files | Transcription + text processing |

All modalities are unified into the same three-layer hierarchy, enabling cross-modal retrieval.

---

## 🚀 Quick Start

### Option 1: Cloud Version

Try MemU instantly without any setup:

👉 **[memu.so](https://memu.so)** - Hosted cloud service with full API access

For enterprise deployment and custom solutions, contact **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer YOUR_API_KEY` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Register a memorization task |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Get task status |
| `POST` | `/api/v3/memory/categories` | List memory categories |
| `POST` | `/api/v3/memory/retrieve` | Retrieve memories (semantic search) |

📚 **[Full API Documentation](https://memu.pro/docs#cloud-version)**

---

### Option 2: Self-Hosted

#### Installation

```bash
pip install -e .
```

#### Basic Example

> **Requirements**: Python 3.13+ and an OpenAI API key

**Test with In-Memory Storage** (no database required):

```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**Test with PostgreSQL Storage** (requires pgvector):

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Run the test
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

Both examples demonstrate the complete workflow:
1. **Memorize**: Process a conversation file and extract structured memory
2. **Retrieve (RAG)**: Fast embedding-based search
3. **Retrieve (LLM)**: Deep semantic understanding search

See [`tests/test_inmemory.py`](tests/test_inmemory.py) and [`tests/test_postgres.py`](tests/test_postgres.py) for the full source code.

---

## 📖 Core APIs

### `memorize()` - Extract and Store Memory

Processes input resources and extracts structured memory:

<img width="100%" alt="memorize" src="assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # File path or URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # Optional: scope to a user
)

# Returns:
{
    "resource": {...},      # Stored resource metadata
    "items": [...],         # Extracted memory items
    "categories": [...]     # Updated category summaries
}
```

### `retrieve()` - Query Memory

Retrieves relevant memory based on queries. MemU supports **two retrieval strategies**:

<img width="100%" alt="retrieve" src="assets/retrieve.png" />

#### RAG-based Retrieval (`method="rag"`)

Fast **embedding vector search** using cosine similarity:

- ✅ **Fast**: Pure vector computation
- ✅ **Scalable**: Efficient for large memory stores
- ✅ **Returns scores**: Each result includes similarity score

#### LLM-based Retrieval (`method="llm"`)

Deep **semantic understanding** through direct LLM reasoning:

- ✅ **Deep understanding**: LLM comprehends context and nuance
- ✅ **Query rewriting**: Automatically refines query at each tier
- ✅ **Adaptive**: Stops early when sufficient information is found

#### Comparison

| Aspect | RAG | LLM |
|--------|-----|-----|
| **Speed** | ⚡ Fast | 🐢 Slower |
| **Cost** | 💰 Low | 💰💰 Higher |
| **Semantic depth** | Medium | Deep |
| **Tier 2 scope** | All items | Only items in relevant categories |
| **Output** | With similarity scores | Ranked by LLM reasoning |

Both methods support:
- **Context-aware rewriting**: Resolves pronouns using conversation history
- **Progressive search**: Categories → Items → Resources
- **Sufficiency checking**: Stops when enough information is retrieved

#### Usage

```python
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "What are their preferences?"}},
        {"role": "user", "content": {"text": "Tell me about work habits"}}
    ],
    where={"user_id": "123"}  # Optional: scope filter
)

# Returns:
{
    "categories": [...],     # Relevant categories (with scores for RAG)
    "items": [...],          # Relevant memory items
    "resources": [...],      # Related raw resources
    "next_step_query": "..." # Rewritten query for follow-up (if applicable)
}
```

**Scope Filtering**: Use `where` to filter by user model fields:
- `where={"user_id": "123"}` - exact match
- `where={"agent_id__in": ["1", "2"]}` - match any in list
- Omit `where` to retrieve across all scopes

> 📚 **For complete API documentation**, see [SERVICE_API.md](docs/SERVICE_API.md) - includes all methods, CRUD operations, pipeline configuration, and configuration types.

---

## 💡 Use Cases

### Example 1: Conversation Memory

Extract and organize memory from multi-turn conversations:

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**What it does:**
- Processes multiple conversation JSON files
- Extracts memory items (preferences, habits, opinions, relationships)
- Generates category markdown files (`preferences.md`, `work_life.md`, etc.)

**Best for:** Personal AI assistants, customer support bots, social chatbots

---

### Example 2: Skill Extraction from Logs

Extract skills and lessons learned from agent execution logs:

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**What it does:**
- Processes agent logs sequentially
- Extracts actions, outcomes, and lessons learned
- Demonstrates **incremental learning** - memory evolves with each file
- Generates evolving skill guides (`log_1.md` → `log_2.md` → `skill.md`)

**Best for:** DevOps teams, agent self-improvement, knowledge management

---

### Example 3: Multimodal Memory

Process diverse content types into unified memory:

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**What it does:**
- Processes documents and images together
- Extracts memory from different content types
- Unifies into cross-modal categories (`technical_documentation`, `visual_diagrams`, etc.)

**Best for:** Documentation systems, learning platforms, research tools

---

## 📊 Performance

MemU achieves **92.09% average accuracy** on the Locomo benchmark across all reasoning tasks.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

View detailed experimental data: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Ecosystem

| Repository | Description | Use Case |
|------------|-------------|----------|
| **[memU](https://github.com/NevaMind-AI/memU)** | Core algorithm engine | Embed AI memory into your product |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend service with CRUD, user system, RBAC | Self-host a memory backend |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Visual dashboard | Ready-to-use memory console |

**Quick Links:**
- 🚀 [Try MemU Cloud](https://app.memu.so/quick-start)
- 📚 [API Documentation](https://memu.pro/docs)
- 💬 [Discord Community](https://discord.gg/memu)

---


---

## 🤝 Partners

<div align="center">

<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="GitHub - openagents-org/openagents: OpenAgents - AI Agent Networks for Open Collaboration"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Milvus" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="Jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="Buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="Bytebase" height="40" style="margin: 10px;"></a>
<a href="https://github.com/LazyAGI/LazyLLM"><img src="assets/partners/LazyLLM.png" alt="LazyLLM" height="40" style="margin: 10px;"></a>

</div>

---

## 📄 License

[Apache License 2.0](LICENSE.txt)

---

## 🌍 Community

- **GitHub Issues**: [Report bugs & request features](NevaMind-AI/memU)
- **Discord**: [Join the community](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [Follow @memU_ai](https://x.com/memU_ai)
- **Contact**: info@nevamind.ai

---

<div align="center">

⭐ **Star us on GitHub** to get notified about new releases!

</div>
