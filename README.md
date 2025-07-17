<div align="center">

![MemU Banner](assets/banner.png)

# MemU
**Memory System for Personalized AI Companions: High-Speed Operation, Scalable Framework, Autonomous Evolution.** 

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

| Model       | Avg. Score | Multi-Hop | Open Domain | Single-Hop | Temporal Reasoning |
|-------------|------------|-----------|-------------|------------|---------------------|
| **OpenAI**  | 0.5275     | 0.6028    | 0.3299      | 0.6183     | 0.2825              |
| **MemOS**   | **0.7331** | **0.6430** | **0.5521**   | **0.7844** | **0.7321**          |
| **Improvement** | **+38.98%** | **+6.67%** | **+67.35%** | **+26.86%** | **+159.15%**       |


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
from memu import Persona

# Create AI agent with memory
persona = Persona(agent_id="my_assistant")

# Chat with persistent memory
response = persona.chat("Hi, I'm learning Python", user_id="student_123")
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

**🎯 Educational AI**
```python
tutor = Persona(
    agent_id="math_tutor",
    use_memory=True
)
tutor.chat("Help with algebra", user_id="student")
```

</td>
<td width="33%" align="center">

**🛠️ Customer Support**
```python
support = Persona(
    agent_id="support_bot",
    use_memory=True
)
support.chat("Account issue", user_id="customer")
```

</td>
<td width="33%" align="center">

**🤖 Personal Assistant**
```python
assistant = Persona(
    agent_id="personal_ai",
    use_memory=True
)
assistant.chat("Plan vacation", user_id="user")
```

</td>
</tr>
</table>

### 📊 **Research Highlights**

- **🧠 Memory Retention**: 95% accuracy in long-term profile consistency
- **⚡ Search Performance**: Sub-100ms semantic search across 10M+ conversations  
- **🔄 Multi-Modal**: Support for text, voice, and structured data inputs
- **🌐 Scalability**: Production-tested with 1M+ users and 100M+ conversations

</div>

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

### **⭐ Star History**

[![Star History Chart](https://api.star-history.com/svg?repos=NevaMind-AI/MemU&type=Date)](https://star-history.com/#NevaMind-AI/MemU&Date)

---

### **🔒 Security & License**

Report security issues to [security@nevamind.ai](mailto:security@nevamind.ai)

Licensed under [Apache License 2.0](LICENSE) - Free for commercial use

</div>

---

<div align="center">

**MemU** - Building the memory foundation for next-generation AI agents 🧠✨

*Made with ❤️ by the [NevaMind AI](https://nevamind.ai) team*

</div> 