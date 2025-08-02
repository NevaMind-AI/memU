<div align="center">

![MemU Banner](assets/banner.png)

# MemU
**Personalized memory for AI companions. Organized.** 

[![PyPI version](https://badge.fury.io/py/memu.svg)](https://badge.fury.io/py/memu)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

<p align="center">
    <a href="https://discord.gg/hQZntfGsbJ" target="_blank">
        <img src="https://img.shields.io/discord/placeholder?logo=discord&labelColor=%20%235462eb&logoColor=%20%23f5f5f5&color=%20%235462eb"
            alt="Discord"></a>
    <a href="https://x.com/Nevamind_ai" target="_blank">
        <img src="https://img.shields.io/twitter/follow/nevamind_ai?logo=X&color=%20%23f5f5f5"
            alt="X (Twitter)"></a>
</p>

<p align="center">
  <a href="./README.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
</p>

MemU is an open-source memory framework specialized for AI companion that gives AI assistants long-term personalized memory. It acts like a "memory folder" managed by the AI itself. The framework finds memories instantly, updates and learns. With it, you can build AIs that truly memories you by continuously updating memories about who you are, what you care about, and your shared experiences, creating companions that grow alongside you.

![MemU Architecture](assets/architecture-overview.png)

</div>

---

## ⭐ Star Us on GitHub

![star-us](https://github.com/NevaMind-AI/MemU/assets/star-us-animation.gif)

**🚀 Join 1,000+ developers building the future of AI memory**

Star MemU to get notified about new releases and join our growing community of AI developers building intelligent agents with persistent memory capabilities.

**💬 Join our Discord community:** [https://discord.gg/hQZntfGsbJ](https://discord.gg/hQZntfGsbJ)

---

MemU is built specifically for AI companions, creating personalized long-term memories through categorized memories, memory connections, evolving insights, and adaptive forgetting. Our framework transforms conversations into files, connects related experiences, grows understanding over time, and prioritizes what matters most - making AI companions feel truly alive and personally connected.

## ✨ Key Features

---

## 📋 **Categorized Memories**

**Your AI companion remembers everything about you, organized and ready**

![Organized Memory Demo](assets/organized-memory-demo.gif)

MemU automatically organizes your conversations into meaningful categories - your hobbies, work life, family stories, and personal preferences. Instead of scattered chat fragments, your AI companion builds a structured understanding of who you are, making every conversation feel personal and contextual.

**Key Benefits:**
- 🗂️ **Document-based storage** - Each memory type is stored as readable documents
- 🏷️ **Smart categorization** - Automatic classification by topics and contexts  
- 🔍 **Easy retrieval** - Quick access to relevant information through categories

---

## 🔗 **Memory Connections**

**Your AI companion connects the dots between your stories**

![Linked Connections Demo](assets/linked-connections-demo.gif)

When you mention your love for hiking, your AI companion remembers you talked about buying boots last month, and connects it to your upcoming mountain trip. These connections help your AI understand the full context of your infomation, making conversations feel natural and insightful.

**Key Benefits:**
- 🕸️ **Smart connections** - Your AI links related memories automatically
- 🔄 **Context awareness** - Previous conversations inform current ones

---

## 🧠 **Evolving Insights**

**Your AI companion learns about you even when you're not chatting**

![Evolved Intelligence Demo](assets/evolved-intelligence-demo.gif)

Even when you're not actively talking to it, your AI companion continuously analyzes your stored memories, discovering new patterns and insights about your preferences, habits, and personality. It's like having a friend who's always thinking about you and getting to know you better in the background.

**Key Benefits:**
- 🤔 **Theory of Mind** - Deep understanding of your mental states and preferences
- 📝 **Self-improvement** - Automatically enhances existing memories
- 🌱 **Continuous learning** - Gets smarter about you over time


---

## 🌫️ **Adaptive Forgetting**

**Your AI companion remembers what matters most**

![Memory Fade Demo](assets/memory-fade-1.gif)

MemU implements an intelligent LRU-like forgetting mechanism where memories naturally fade in importance without disappearing entirely. This mimics human memory patterns - rarely accessed information becomes less prominent while frequently referenced memories gain stronger relevance.

**Key Benefits:**
- ⏰ **Time-based decay** - Unused memories naturally fade in importance
- 🔄 **Usage-based boost** - Recently accessed memories gain higher relevance
- 💾 **Never truly lost** - Information fades but remains retrievable when needed
- 🎯 **Smart prioritization** - Most relevant memories surface first in conversations

---

## 🏆 **Competitive Advantages**

![Competitive Analysis](assets/competitive-analysis.png)

**Why MemU stands out from other memory solutions**

### 🎯 **Higher Memory Accuracy**

MemU achieves **92.09% average accuracy** across all reasoning tasks, significantly outperforming competitors.

| Model    |   Single-Hop |  Multi-Hop | Open Domain | Temporal Reasoning | Avg. Score | 
|-------------|------------|-----------|-------------|------------|---------------------|
| **OpenAI**  | 63.79      | 42.92     | 62.29       | 21.71      | 52.90               |
| **Mem0**    | 67.13      | 51.15     | 72.93       | 55.51      | 66.88               |          |
| **Memobase** | 70.92     | 46.88     | 77.17       | 85.05      | 75.78               |
| **Zep**     | 74.11      | 66.04     | 67.71       | 79.76      | 75.14               |            |
| **MemU**    | **94.88**  | **88.30**  | 77.08      | **92.52**   | **92.09**  |

*Based on comprehensive benchmarks against other memory frameworks*

---

### 🔄 **Flexible Retrieval Strategies**


**Multiple recall methods for every use case**

MemU provides a comprehensive suite of retrieval strategies, allowing you to choose the optimal approach for your specific scenario. From semantic similarity to category search, our flexible system adapts to your needs.

**Available Strategies:**

- 🔍 **Semantic Search** - Find memories by meaning and context using advanced embedding models. Perfect for natural language queries and conceptual searches that go beyond keyword matching.

- 🏷️ **Category-based Retrieval** - Organize memories through topic category classification. Ideal for structured information retrieval and domain-specific searches.

- 🔗 **Graph Traversal** - Discover related information by following memory connections and relationship networks. Enables exploration of indirect relationships and contextual paths between concepts.

- 🎯 **Hybrid Fusion** - Combine multiple strategies using ensemble methods. Delivers optimal performance for complex queries requiring maximum accuracy.

- 🧠 **Active Retrieval** - Determine when to retrieve memories based on conversation context and relevance. Prevents unnecessary retrievals while ensuring important memories are surfaced when needed.
---

### 📖 **Human-Readable Memory Format**

**Memories you can actually read and understand**

Unlike other memory frameworks that store information as fragmented sentences, MemU organizes memories as **coherent, readable documents**. While competitors break down information into scattered fragments, MemU maintains context and structure, enabling easy debugging, manual editing, and seamless integration with existing workflows.

**Readability Benefits:**
- 📝 **Document Structure** - Organized as markdown files with clear headers
- 🔗 **Wiki-like Links** - Documents with interconnected links enabling seamless navigation between related memories
- 📋 **Export Friendly** - Standard formats compatible with any system

---



## 🚀 Quick Start

### **Installation in 30 seconds**

```bash
# Install MemU with all features
pip install memu-py
```

### **3-Line Demo**

```python
from memu.memory import MemoryAgent
from memu.llm import OpenAIClient

# Create AI agent with unified memory
memory_agent = MemoryAgent(llm_client=OpenAIClient(), memory_dir="memory")

# Process conversation with persistent memory
results = memory_agent.process_conversation("Hi, I'm learning Python", "student_123")
```

![Quick Start Demo](assets/quickstart-demo.gif)

### **Live Demo**

Try MemU instantly in your browser: [**🔗 Interactive Demo**](https://demo.nevamind.ai)

---

## 📚 Usage Guide & Research Highlights

<div align="center">

![Use Cases Demo](assets/use-cases-demo.gif)

### 🎓 **Use Cases**

<table>
<tr>
<td width="33%" align="center">


**🤖 Personal Assistant**

**🎯 Role play**

**🛠️ AI companion**

**🎯 Educational AI**

** note类ai **


**Creation Support**
---

## 🤝 Contributing

![Contributing Flow](assets/contributing-flow.png)

### **Join Our Mission**

Help us build the future of AI memory! We welcome contributions of all kinds.

**🌟 Ways to Contribute:**
- 🐛 Report bugs and suggest features
- 📝 Improve documentation and examples  
- 🔧 Add new LLM providers and integrations
- 🧪 Write tests and improve code quality

### **Quick Contribution Guide**

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/MemU.git

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes and test
pip install -e .
python -m pytest

# 4. Submit PR
git push origin feature/amazing-feature
```

**🎯 Current Priorities:**
- Multi-modal memory support (images, audio)
- Performance optimizations
- Additional embedding providers
- Enterprise security features

---

## 🌍 Community

<table>
<tr>
<td width="50%">

![Community Network](assets/community-network.gif)

</td>
<td width="50%">

![Global Users](assets/global-users-map.png)

</td>
</tr>
</table>

### **Connect with the MemU Community**

<a href="https://discord.gg/your-discord-server">
    <img src="https://img.shields.io/badge/Discord-Join%20Chat-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord">
</a>
<a href="https://github.com/NevaMind-AI/MemU/discussions">
    <img src="https://img.shields.io/badge/GitHub-Discussions-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Discussions">
</a>
<a href="https://twitter.com/nevamind_ai">
    <img src="https://img.shields.io/badge/X-Follow-1DA1F2?style=for-the-badge&logo=x&logoColor=white" alt="X (Twitter)">
</a>

### **📞 Get Support**

| Channel | Best For |
|---------|----------|
| 💬 [Discord](https://discord.gg/your-discord-server) | Real-time chat, community help |
| 🗣️ [GitHub Discussions](https://github.com/NevaMind-AI/MemU/discussions) | Feature requests, Q&A |
| 🐛 [GitHub Issues](https://github.com/NevaMind-AI/MemU/issues) | Bug reports, technical issues |
| 📧 [Email](mailto:contact@nevamind.ai) | Enterprise inquiries, partnerships |

### **🏆 Contributors**

<a href="https://github.com/NevaMind-AI/MemU/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=NevaMind-AI/MemU" />
</a>


### **🔒 Security & License**

Report security issues to [security@nevamind.ai](mailto:security@nevamind.ai)

Licensed under [Apache License 2.0](LICENSE)

---

![AI Memory Animation](assets/ai-memory-animation.gif)

**MemU** - Building the memory foundation for next-generation AI agents 🧠✨

*Made with ❤️ by the [NevaMind AI](https://nevamind.ai) team*

![Footer Decoration](assets/footer-decoration.png) 