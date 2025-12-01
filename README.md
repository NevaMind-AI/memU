<div align="center">

![MemU Banner](assets/banner.png)

### MemU: A Future-Oriented Agentic Memory System

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)
</div>

MemU is an agentic memory framework for LLM and AI agent backends. It receive multi-modal inputs, extracts them into memory items, and then organizes and summarizes these items into structured memory files.

Unlike traditional RAG systems that rely solely on embedding-based search, MemU supports **non-embedding retrieval** through direct file reading. The LLM comprehends natural language memory files directly, enabling deep search by progressively tracking from categories → items → original resources.

MemU offers several convenient ways to get started right away:

- **One call = response + memory**
  👉 memU Response API: https://memu.pro/docs#responseapi

- **Try it instantly**
  👉 https://app.memu.so/quick-start
---

## ⭐ Star Us on GitHub

Star MemU to get notified about new releases and join our growing community of AI developers building intelligent agents with persistent memory capabilities.
![star-us](https://github.com/user-attachments/assets/913dcd2e-90d2-4f62-9e2d-30e1950c0606)

**💬 Join our Discord community:** [https://discord.gg/memu](https://discord.gg/memu)

---
## Roadmap

MemU v0.3.0 has been released! This version initializes the memorize and retrieve workflows with the new 3-layer architecture.

Starting from this release, MemU will roll out multiple features in the short- to mid-term:

### Core capabilities iteration
- [x] **Multi-modal enhancements** – Support for images, audio, and video
- [ ] **Intention** – Higher-level decision-making and goal management
- [ ] **Multi-client support** – Switch between OpenAI, Deepseek, Gemini, etc.
- [ ] **Data persistence expansion** – Support for Postgres, S3, DynamoDB
- [ ] **Benchmark tools** – Test agent performance and memory efficiency
- [ ] ……

### Upcoming open-source repositories
- [ ] **memU-ui** – The web frontend for MemU, providing developers with an intuitive and visual interface
- [ ] **memU-server** – Powers memU-ui with reliable data support, ensuring efficient reading, writing, and maintenance of agent memories

## 🧩 Why MemU?

Most memory systems in current LLM pipelines rely heavily on explicit modeling, requiring manual definition and annotation of memory categories. This limits AI’s ability to truly understand memory and makes it difficult to support diverse usage scenarios.

MemU offers a flexible and robust alternative, inspired by hierarchical storage architecture in computer systems. It progressively transforms heterogeneous input data into queryable and interpretable textual memory.

Its core architecture consists of three layers: **Resource Layer → Memory Item Layer → MemoryCategory Layer.**

<img width="1363" height="563" alt="Three-Layer Architecture Diagram" src="https://github.com/user-attachments/assets/06029141-7068-4fe8-bf50-377cc6f80c87" />

- **Resource Layer:** Multimodal raw data warehouse
- **Memory Item Layer:** Discrete extracted memory units
- **MemoryCategory Layer:** Aggregated textual memory units

**Key Features:**

- **Full Traceability:** Track from raw data → items → documents and back
- **Memory Lifecycle:** Memorization → Retrieval → Self-evolution
- **Two Retrieval Methods:**
  - **RAG-based**: Fast embedding vector search
  - **LLM-based**: Direct file reading with deep semantic understanding
- **Self-Evolving:** Adapts memory structure based on usage patterns

<img width="1365" height="308" alt="process" src="https://github.com/user-attachments/assets/cabed021-f231-4bd2-9bb5-7c8cdb5f928c" />


## 🚀 Get Started

### Installation

```bash
pip install memu-py
```

### Quick Example

> **⚠️ Important**: Ensure you have Python 3.14+

> **⚠️ Important**: Replace `"your-openai-api-key"` with your actual OpenAI API key to use the service.

```python
from memu.app import MemoryService
import os

async def main():
    api_key = "your-openai-api-key"
    file_path = os.path.abspath("path/to/memU/tests/example/example_conversation.json")

    # Initialize service with RAG method
    service_rag = MemoryService(
        llm_config={"api_key": api_key},
        embedding_config={"api_key": api_key},
        retrieve_config={"method": "rag"}
    )

    # Memorize
    memory = await service_rag.memorize(resource_url=file_path, modality="conversation")
    for cat in memory.get('categories', []):
        print(f"  - {cat.get('name')}: {(cat.get('summary') or '')[:80]}...")

    queries = [
        {"role": "user", "content": {"text": "Tell me about preferences"}},
        {"role": "user", "content": {"text": "What are their habits?"}}
    ]

    # RAG-based retrieval
    print("\n[RETRIEVED - RAG]")
    result_rag = await service_rag.retrieve(queries=queries)
    for item in result_rag.get('items', [])[:3]:
        print(f"  - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")

    # Initialize service with LLM method (reuse same memory store)
    service_llm = MemoryService(
        llm_config={"api_key": api_key},
        embedding_config={"api_key": api_key},
        retrieve_config={"method": "llm"}
    )
    service_llm.store = service_rag.store  # Reuse memory store

    # LLM-based retrieval
    print("\n[RETRIEVED - LLM]")
    result_llm = await service_llm.retrieve(queries=queries)
    for item in result_llm.get('items', [])[:3]:
        print(f"  - [{item.get('memory_type')}] {item.get('summary', '')[:100]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Retrieval Methods

**RAG-based (`method="rag"`)**: Fast embedding vector search for large-scale data

**LLM-based (`method="llm"`)**: Deep semantic understanding through direct file reading

Both support:
- **Context-aware rewriting**: Resolves pronouns using conversation history
- **Progressive search**: Categories → Items → Resources
- **Next-step suggestions**: Iterative multi-turn retrieval

---

## 💡 Use Cases

MemU provides practical examples demonstrating different memory extraction and organization scenarios. Each example showcases a specific use case with real-world applications.

### **Use Case 1: Conversation Memory Processing**

Extract and organize memory from multi-turn conversations. Perfect for:
- Personal AI assistants that remember user preferences and history
- Customer support bots maintaining conversation context
- Social chatbots building user profiles over time

**Example:** Process multiple conversation files and automatically categorize memories into personal_info, preferences, work_life, relationships, etc.

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**What it does:**
- Processes conversation JSON files
- Extracts memory items (preferences, habits, opinions)
- Organizes into structured categories
- Generates readable markdown files for each category

### **Use Case 2: Skill Extraction from Logs**

Extract skills and lessons learned from agent execution logs. Ideal for:
- DevOps teams learning from deployment experiences
- Agent systems improving through iterative execution
- Knowledge management from operational logs

**Example:** Process deployment logs incrementally, learning from each attempt to build a comprehensive skill guide.

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**What it does:**
- Processes agent logs sequentially
- Extracts actions, outcomes, and lessons learned
- Demonstrates **incremental learning** (memory evolves with each file)
- Generates evolving skill guides (log_1.md → log_2.md → log_3.md → skill.md)

**Key Feature:** Shows MemU's core strength - continuous memory updates. Each file updates existing memory, and category summaries evolve progressively.

### **Use Case 3: Multimodal Memory Processing**

Process diverse content types (documents, images, videos) into unified memory. Great for:
- Documentation systems processing mixed media
- Learning platforms combining text and visual content
- Research tools analyzing multimodal data

**Example:** Process technical documents and architecture diagrams together, creating unified memory categories.

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**What it does:**
- Processes multiple modalities (text documents, images)
- Extracts memory from different content types
- Unifies memories into cross-modal categories
- Creates organized documentation (technical_documentation, architecture_concepts, code_examples, visual_diagrams)

---


### **📄 License**

By contributing to MemU, you agree that your contributions will be licensed under the **Apache License 2.0**.

---

## 🌍 Community
For more information please contact info@nevamind.ai

- **GitHub Issues:** Report bugs, request features, and track development. [Submit an issue](https://github.com/NevaMind-AI/memU/issues)

- **Discord:** Get real-time support, chat with the community, and stay updated. [Join us](https://discord.com/invite/hQZntfGsbJ)

- **X (Twitter):** Follow for updates, AI insights, and key announcements. [Follow us](https://x.com/memU_ai)

---

## 🤝 Ecosystem

We're proud to work with amazing organizations:

<div align="center">

### Development Tools
<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://github.com/openagents-org/openagents"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="bytebase" height="40" style="margin: 10px;"></a>
<a href="https://github.com/LazyAGI/LazyLLM"><img src="assets/partners/LazyLLM.png" alt="LazyLLM" height="40" style="margin: 10px;"></a>
</div>

---

*Interested in partnering with MemU? Contact us at [contact@nevamind.ai](mailto:contact@nevamind.ai)*
