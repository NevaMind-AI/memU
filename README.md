<div align="center">

![MemU Banner](assets/banner.png)

<h3>memU: The Next-Gen Memory Framework for AI Companions</h3>

[![PyPI version](https://badge.fury.io/py/memu.svg)](https://badge.fury.io/py/memu)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/Nevamind_ai)
[![Reddit](https://img.shields.io/badge/Reddit-Join%20Community-FF4500?logo=reddit&logoColor=white)](https://reddit.com/r/MemU)
[![WeChat](https://img.shields.io/badge/WeChat-微信群-07C160?logo=wechat&logoColor=white)](#)
</div>

**MemU** is an open-source memory framework for AI companions—high accuracy, fast retrieval, low cost. It acts as an intelligent "memory folder" that adapts to different AI companion scenarios.

With **memU**, you can build AI companions that truly remember you. They learn who you are, what you care about, and grow alongside you through every interaction.

### 🥇 92.9% Accuracy - 💰 90% Cost Reduction - 🤖 AI Companion Specialized
- ✅ **AI Companion Specialization** - Adapt to AI companions application
- ✅ **92.9% Accuracy** - State-of-the-art score in Locomo benchmark
- ✅ **Up to 70% Cost Reduction** - Through optimized infrastructure
- ✅ **Advanced Retrieval Strategies** - Multiple methods including semantic search, hybrid search, contextual retrieval
- ✅ **24/7 Support** - For enterprise customers

---

## ⭐ Star Us on GitHub

Star MemU to get notified about new releases and join our growing community of AI developers building intelligent agents with persistent memory capabilities.

![star-us](./assets/star.gif)

**💬 Join our Discord community:** [https://discord.gg/hQZntfGsbJ](https://discord.gg/hQZntfGsbJ)

---

## 🚀Get Started

There are three ways to get started with MemU:

### ☁️ Cloud Version ([Online Platform](https://memu.so))

The fastest way to integrate your application with memU. Perfect for teams and individuals who want immediate access without setup complexity. We host the models, APIs, and cloud storage, ensuring your application gets the best quality AI memory.

- **Instant Access** - Start integrating AI memories in minutes
- **Managed Infrastructure** - We handle scaling, updates, and maintenance for optimal memory quality
- **Premium Support** - Subscribe and get priority assistance from our engineering team

#### Step-by-step

**Step 1:** Create account & get your API key
Go to https://app-preview.memu.so/api-key/ for generating api-keys.
**Step 2:** Add three lines to your code
```python
pip install memu-py

# Example usage
from memu.sdk import MemuClient
```

**Step 3:** Quick Start
```python
import openai
from memu.sdk import MemuClient

# Initialize
memu_client = MemuClient(
    base_url="https://api-preview.memu.so", 
    api_key=os.getenv("MEMU_API_KEY")
)
```

📖 **See [`example/openai_chat_example.py`](example/openai_chat_example.py) for complete integration details**

✨ **That's it!** MemU remembers everything and helps your AI learn from past conversations.


### 🏢 Enterprise Edition

For organizations requiring maximum security, customization, control and best quality:

- **Commercial License** - Full proprietary features, commercial usage rights, white-labeling options
- **Custom Development** - SSO/RBAC integration, dedicated algorithm team for scenario-specific framework optimization
- **Intelligence & Analytics** - User behavior analysis, real-time production monitoring, automated agent optimization
- **Premium Support** - 24/7 dedicated support, custom SLAs, professional implementation services

📧 **Enterprise Inquiries:** [contact@nevamind.ai](mailto:contact@nevamind.ai)


### 🏠 Self-Hosting (Community Edition)
For users and developers who prefer local control, data privacy, or customization:

* **Data Privacy** - Keep sensitive data within your infrastructure
* **Customization** - Modify and extend the platform to fit your needs
* **Cost Control** - Avoid recurring cloud fees for large-scale deployments

🚀 **Coming Soon!**

---


## ✨ Key Features

### Autonomous Memory Management System

![features](./assets/workflow.png)

### **Organize** - Autonomous Memory Management
Your memories are structured as intelligent folders managed by a memory agent. We do not do explicit modeling for memories. The memory agent automatically decides what to record, modify, or archive. Think of it as having a personal librarian who knows exactly how to organize your thoughts.

### **Link** - Interconnected Knowledge Graph
Memories don't exist in isolation. Our system automatically creates meaningful connections between related memories, building a rich network of hyperlinked documents and transforming memory discovery from search into effortless recall.

### **Evolve** - Continuous Self-Improvement
Even when offline, your memory agent keeps working. It generates new insights by analyzing existing memories, identifies patterns, and creates summary documents through self-reflection. Your knowledge base becomes smarter over time, not just larger.

### **Never Forget** - Intelligent Retention System
The memory agent automatically prioritizes information based on usage patterns. Recently accessed memories remain highly accessible, while less relevant content is deprioritized or forgotten. This creates a personalized information hierarchy that evolves with your needs.
---

## 🤫 Advantages

### Higher Memory Accuracy
MemU achieves 92.09% average accuracy across all reasoning tasks, significantly outperforming competitors. Technical Report will be published soon!

![Memory Accuracy Comparison](assets/benchmark.png)

### Flexible Retrieval Strategies

MemU provides a comprehensive suite of retrieval strategies, allowing you to choose the optimal approach for your specific scenario. From semantic similarity to category search, our flexible system adapts to your needs.

### Readable Memory Format

Unlike other memory frameworks that store information as fragmented sentences, MemU organizes memories as coherent, readable documents while simultaneously transforming raw data into structured. MemU maintains complete context and relationships, enabling easy debugging, manual editing, seamless analytics, and effortless integration with existing workflows.


---
## 🎓 **Use Cases**

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="assets/usecase/ai_companion-0000.jpg" width="150" height="100"><br>**AI Companion** | <img src="assets/usecase/ai_role_play-0000.jpg" width="150" height="100"><br>**AI Role Play** | <img src="assets/usecase/ai_ip-0000.png" width="150" height="100"><br>**AI IP Character** | <img src="assets/usecase/ai_edu-0000.jpg" width="150" height="100"><br>**AI Education** |
| <img src="assets/usecase/ai_therapy-0000.jpg" width="150" height="100"><br>**AI Therapy** | <img src="assets/usecase/ai_robot-0000.jpg" width="150" height="100"><br>**AI Robot** | <img src="assets/usecase/ai_creation-0000.jpg" width="150" height="100"><br>**AI Creation** | More|
---

## 🤝 Contributing

We build trust through open-source collaboration. Your creative contributions drive memU's innovation forward. Explore our GitHub issues and projects to get started and make your mark on the future of memU.

📋 **[Read our detailed Contributing Guide →](CONTRIBUTING.md)**


### **📄 License**

By contributing to MemU, you agree that your contributions will be licensed under the **Apache License 2.0**.

---

## 🌍 Community
For more information please contact info@nevamind.ai

- **GitHub Issues:** Report bugs, request features, and track development. [Submit an issue]()

- **Discord:** Get real-time support, chat with the community, and stay updated. [Join us](https://discord.memu.org/)

- **X (Twitter):** Follow for updates, AI insights, and key announcements. [Follow us]()



