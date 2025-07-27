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

MemU outperforms other memory solutions in multiple reasoning tasks.

| Model    |   Single-Hop |  Multi-Hop | Open Domain | Temporal Reasoning | Avg. Score | 
|-------------|------------|-----------|-------------|------------|---------------------|
| **OpenAI**  | 63.79      | 42.92     | 62.29       | 21.71      | 52.90               |
| **Mem0**    | 67.13      | 51.15     | 72.93       | 55.51      | 66.88               |
| **Mem0ᵍ**   | 65.71      | 47.19     | 75.71       | 58.13      | 68.44               |
| **Memobase** | 70.92     | 46.88     | 77.17       | 85.05      | 75.78               |
| **Zep**     | 74.11      | 66.04     | 67.71       | 79.76      | 75.14               |
| **MIRIX**   | 85.11      | 83.70     | 65.62       | 88.39      | 85.38               |
| **MemU**    | **94.9**  | **88.3**  | **77.1**    | **92.5**   | **92.09**  |

model : gpt-4.1-mini
---

## ✨ Key Features

<div align="center">

### 🧠 **Specialized for AI companion**
![Memory Demo](assets/memory-demo.gif)
*Automatic profile updates and event tracking across conversations*
#### user reminder
#### important event
#### user profile
#### memory ranking
#### forget memory





### 🔍 **Retrieval Fast**
![Search Demo](assets/search-demo.gif)


### 🎯 **Extension Framework**
![Psychology Demo](assets/psychology-demo.gif)




### **Self Evolvement**


</div>



---
## 🤖 **Memory as documents** 
![LLM Integration](assets/llm-integration.gif)

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

### 🎓 **Use Cases**

<table>
<tr>
<td width="33%" align="center">


**🤖 Personal Assistant**

**🎯 Role play**

**🎯 Educational AI**

**🛠️ Customer Support**

**Creation Support**
---

## 🤝 Contributing

<div align="center">

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

**MemU** - Building the memory foundation for next-generation AI agents 🧠✨

*Made with ❤️ by the [NevaMind AI](https://nevamind.ai) team*

</div> 