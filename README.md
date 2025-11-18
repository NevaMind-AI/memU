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

- **Resource Layer:**
  A multimodal raw data warehouse, also serving as the ground truth layer, providing a semantic foundation for the memory system.

- **Memory Item Layer:**
  A unified semantic abstraction layer, functioning as the system’s semantic cache, supplying high-density semantic vectors for downstream retrieval and reasoning.

- **MemoryCategory Layer:**
  A thematic document layer, mimicking human working memory mechanisms, balancing short-term response efficiency and long-term information completeness.

Through this three-layer design, **MemU brings genuine memory into the agent layer, achieving:**

- **Full Traceability:**
  Complete traceability across the three layers—from raw data → memory items → aggregated documents. Enables bidirectional tracking of each knowledge piece’s source and evolution, ensuring transparency and interpretability.

- **End-to-End Memory Lifecycle Management:**
  The three core processes correspond to the memory lifecycle: **Memorization → Retrieval → Self-evolution**.

- **Coherent and Scalable Memorization:**
  During memorization, the system maintains memory coherence while automatically managing resources to support sustainable expansion.

- **Efficient and Interpretable Retrieval:**
  Retrieves information efficiently while preserving interpretability, supporting cross-theme and cross-modal semantic queries and reasoning. The system offers two retrieval methods:
  - **RAG-based Retrieval**: Fast embedding-based vector search for efficient large-scale retrieval
  - **LLM-based Retrieval**: Direct file reading through natural language understanding, allowing deep search by tracking step-by-step from categories → items → original resources without relying on embedding search

- **Self-Evolving Memory:**
  A feedback-driven mechanism continuously adapts the memory structure according to real usage patterns.
<img width="1365" height="308" alt="process" src="https://github.com/user-attachments/assets/cabed021-f231-4bd2-9bb5-7c8cdb5f928c" />


## 🚀Get Started

### Installation

```bash
pip install memu-py
```

### Basic Usage

```python
from memu.app import MemoryUser
import logging

async def test_memory_service():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("memu")
    logger.setLevel(logging.DEBUG)

    # Initialize MemoryUser with your OpenAI API key
    service = MemoryUser(llm_config={"api_key": "your-openai-api-key"})

    # Memorize a conversation
    memory = await service.memorize(
        resource_url="tests/data/example_conversation.json",
        modality="conversation"
    )

    # Example conversation history for query rewriting
    conversation_history = [
        {"role": "user", "content": "Tell me about the user's preferences"},
        {"role": "assistant", "content": "I'd be happy to help. Let me search the memory."},
        {"role": "user", "content": "What are their habits?"}
    ]

    # Test 1: RAG-based Retrieval with conversation history
    print("\n[Test 1] RAG-based Retrieval with conversation history")
    retrieved_rag = await service.retrieve(
        query="What are their habits?",
        conversation_history=conversation_history,
        retrieve_config={"method": "rag", "top_k": 5}
    )
    print(f"Needs retrieval: {retrieved_rag.get('needs_retrieval')}")
    print(f"Original query: {retrieved_rag.get('original_query')}")
    print(f"Rewritten query: {retrieved_rag.get('rewritten_query')}")
    print(f"Results: {len(retrieved_rag.get('categories', []))} categories, "
          f"{len(retrieved_rag.get('items', []))} items")

    # Test 2: LLM-based Retrieval with conversation history
    print("\n[Test 2] LLM-based Retrieval with conversation history")
    retrieved_llm = await service.retrieve(
        query="What are their habits?",
        conversation_history=conversation_history,
        retrieve_config={"method": "llm", "top_k": 5}
    )
    print(f"Needs retrieval: {retrieved_llm.get('needs_retrieval')}")
    print(f"Original query: {retrieved_llm.get('original_query')}")
    print(f"Rewritten query: {retrieved_llm.get('rewritten_query')}")
    print(f"Results: {len(retrieved_llm.get('categories', []))} categories, "
          f"{len(retrieved_llm.get('items', []))} items")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_memory_service())
```

### Understanding Retrieval Methods

MemU provides two distinct retrieval approaches, each optimized for different scenarios:

#### **1. RAG-based Retrieval (`method="rag"`)**
Fast embedding-based vector search using cosine similarity. Ideal for:
- Large-scale datasets
- Real-time performance requirements
- Cost-effective retrieval at scale

The system progressively searches through three layers:
1. **Category Layer**: Searches category summaries
2. **Item Layer**: Searches memory items within relevant categories
3. **Resource Layer**: Tracks back to original multimodal resources (conversations, documents, videos, etc.)

At each tier, the system judges if sufficient information has been found and dynamically rewrites the query with context for deeper search.

#### **2. LLM-based Retrieval (`method="llm"`)**
Direct file reading through natural language understanding. Ideal for:
- Complex semantic queries requiring nuanced understanding
- Deep contextual reasoning
- Scenarios where interpretability is critical

This method uses the LLM to:
- Read and comprehend natural language memory files directly
- Rank results based on semantic relevance
- Provide reasoning for each ranked result
- Track step-by-step from categories → items → original resources **without relying on embeddings**

Both methods support:
- **Full traceability**: Each retrieved item includes its `resource_id`, allowing you to trace back to the original source
- **Conversation-aware rewriting**: Automatically resolves pronouns and references using conversation history
- **Pre-retrieval decision**: Intelligently determines if memory retrieval is needed for the query
- **Progressive search**: Stops early if sufficient information is found at higher layers



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


