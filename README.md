<div align="center">

![MemU Banner](assets/banner.png)

# MemU
**Your Personalized AI memory. Organized.** 

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
  <a href="./README_CN.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
  <a href="./README_JA.md"><img alt="日本語" src="https://img.shields.io/badge/日本語-d9d9d9"></a>
  <a href="./README_KR.md"><img alt="한국어" src="https://img.shields.io/badge/한국어-d9d9d9"></a>
</p>

MemU is an open-source memory framework for personalized AI companions. We treat memory as an agent-controlled file system that stores user information as documents. It provides high-speed memory retrieval and enables self-evolution without interacting with users. The framework is easily extendable, enabling you to create AI companions that genuinely remember and grow with their users.

![MemU Architecture](assets/architecture-overview.png)

</div>

---

## ⭐ Star Us on GitHub

<div align="center">

![star-us](https://github.com/NevaMind-AI/MemU/assets/star-us-animation.gif)

**🚀 Join 1,000+ developers building the future of AI memory**

Star MemU to get notified about new releases and join our growing community of AI developers building intelligent agents with persistent memory capabilities.

</div>

---

## 📈 Performance Benchmark

<div align="center">

![Performance Chart](assets/performance-chart.png)

MemU outperforms other memory solutions in multiple reasoning tasks.

</div>

| Model    |   Single-Hop |  Multi-Hop | Open Domain | Temporal Reasoning | Avg. Score | 
|-------------|------------|-----------|-------------|------------|---------------------|
| **OpenAI**  | 63.79      | 42.92     | 62.29       | 21.71      | 52.90               |
| **Mem0**    | 67.13      | 51.15     | 72.93       | 55.51      | 66.88               |
| **Mem0ᵍ**   | 65.71      | 47.19     | 75.71       | 58.13      | 68.44               |
| **Memobase** | 70.92     | 46.88     | 77.17       | 85.05      | 75.78               |
| **Zep**     | 74.11      | 66.04     | 67.71       | 79.76      | 75.14               |
| **MIRIX**   | 85.11      | 83.70     | 65.62       | 88.39      | 85.38               |
| **MemU**    | **94.88**  | **88.30**  | **77.08**    | **92.52**   | **92.09**  |

model : gpt-4.1-mini
---

## ✨ Key Features

---

## 📋 **Organized Memory**

<div align="center">

**Transform chaotic information into structured knowledge**

![Organized Memory Demo](assets/organized-memory-demo.gif)

</div>

MemU intelligently organizes memories into well-structured documents, creating a coherent knowledge base that grows with each interaction. Unlike traditional memory systems that store isolated fragments, MemU maintains contextual relationships and categorical organization.

**Key Benefits:**
- 🗂️ **Document-based storage** - Each memory type is stored as readable documents
- 🏷️ **Smart categorization** - Automatic classification by topics and contexts  
- 🔍 **Easy retrieval** - Quick access to relevant information through semantic search
- 📊 **Structured format** - Consistent organization across all memory types

---

## 🔗 **Linked Connections**

<table align="center">
<tr>
<td width="50%">

**Build a web of interconnected knowledge**

Different memories are interconnected through sophisticated semantic relationships, creating a rich network of contextual associations. This enables the AI to understand not just individual facts, but how concepts relate to each other across different conversations and contexts.

**Key Benefits:**
- 🕸️ **Semantic linking** - Memories connect based on meaning and context
- 🔄 **Cross-referencing** - Related information surfaces automatically
- 🧩 **Contextual understanding** - AI grasps relationships between different topics
- 📈 **Knowledge graph** - Dynamic network that expands with each interaction

</td>
<td width="50%">

![Linked Connections Demo](assets/linked-connections-demo.gif)

</td>
</tr>
</table>

---

## 🧠 **Evolved Intelligence**

<table align="center">
<tr>
<td width="50%">

![Evolved Intelligence Demo](assets/evolved-intelligence-demo.gif)

</td>
<td width="50%">

**Self-improving AI that grows smarter over time**

The Memory Agent continuously performs Theory of Mind reasoning, analyzing stored memories to generate deeper insights about user preferences, behaviors, and needs. This creates an evolving understanding that enhances existing documents and generates new knowledge automatically.

**Key Benefits:**
- 🤔 **Theory of Mind** - Deep understanding of user mental states and preferences
- 📝 **Self-enhancement** - Automatically improves existing memory documents
- 💡 **Insight generation** - Creates new understanding from existing information
- 🌱 **Continuous growth** - Knowledge base becomes more sophisticated over time

</td>
</tr>
</table>

---

## 🌫️ **Fade Memory**

<div align="center">

**Natural forgetting that preserves what matters**

<table>
<tr>
<td width="33%">

![Memory Fade 1](assets/memory-fade-1.gif)

</td>
<td width="34%">

![Memory Fade 2](assets/memory-fade-2.gif)

</td>
<td width="33%">

![Memory Fade 3](assets/memory-fade-3.gif)

</td>
</tr>
</table>

</div>

MemU implements an intelligent LRU-like forgetting mechanism where memories naturally fade in importance without disappearing entirely. This mimics human memory patterns - rarely accessed information becomes less prominent while frequently referenced memories gain stronger relevance.

**Key Benefits:**
- ⏰ **Time-based decay** - Unused memories naturally fade in importance
- 🔄 **Usage-based boost** - Recently accessed memories gain higher relevance
- 💾 **Never truly lost** - Information fades but remains retrievable when needed
- 🎯 **Smart prioritization** - Most relevant memories surface first in conversations

---


## 🚀 Quick Start

<div align="center">

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

</div>

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

**🛠️ Customer Support**


**Creation Support**
---

## 🤝 Contributing

<div align="center">

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

</div>

---

## 🌍 Community

<div align="center">

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

<p align="center">
    <a href="https://discord.gg/your-discord-server">
        <img src="https://img.shields.io/badge/Discord-Join%20Chat-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord">
    </a>
    <a href="https://github.com/NevaMind-AI/MemU/discussions">
        <img src="https://img.shields.io/badge/GitHub-Discussions-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Discussions">
    </a>
    <a href="https://twitter.com/nevamind_ai">
        <img src="https://img.shields.io/badge/X-Follow-1DA1F2?style=for-the-badge&logo=x&logoColor=white" alt="X (Twitter)">
    </a>
</p>

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

</div>

---

<div align="center">

![AI Memory Animation](assets/ai-memory-animation.gif)

**MemU** - Building the memory foundation for next-generation AI agents 🧠✨

*Made with ❤️ by the [NevaMind AI](https://nevamind.ai) team*

![Footer Decoration](assets/footer-decoration.png)

</div> 