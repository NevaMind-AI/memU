<div align="center">

![MemU Banner](assets/banner.png)

### MemU: The Next-Gen Memory Framework for AI Companions

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)
</div>

**MemU** is an open-source memory framework for AI companions—high accuracy, fast retrieval, low cost. It acts as an intelligent "memory folder" that adapts to different AI companion scenarios.

 With **memU**, you can build AI companions that truly remember you. They learn who you are, what you care about, and grow alongside you through every interaction. 

 Visit our homepage: [memu.pro](https://memu.pro/)

### 🥇 92% Accuracy - 💰 90% Cost Reduction - 🤖 AI Companion Specialized
- ✅ **AI Companion Specialization** - Adapt to AI companions application
- ✅ **92% Accuracy** - State-of-the-art score in Locomo benchmark
- ✅ **Up to 90% Cost Reduction** - Through optimized online platform
- ✅ **Advanced Retrieval Strategies** - Multiple methods including semantic search, hybrid search, contextual retrieval
- ✅ **24/7 Support** - For enterprise customers

---

## ⭐ Star Us on GitHub

Star MemU to get notified about new releases and join our growing community of AI developers building intelligent agents with persistent memory capabilities.

![star-us](./assets/star.gif)

**💬 Join our Discord community:** [https://discord.gg/memu](https://discord.gg/memu)

---

## 🚀Get Started

There are three ways to get started with MemU:

### ☁️ Cloud Version ([Online Platform](https://app.memu.so))

The fastest way to integrate your application with memU. Perfect for teams and individuals who want immediate access without setup complexity. We host the models, APIs, and cloud storage, ensuring your application gets the best quality AI memory.

- **Instant Access** - Start integrating AI memories in minutes
- **Managed Infrastructure** - We handle scaling, updates, and maintenance for optimal memory quality
- **Premium Support** - Subscribe and get priority assistance from our engineering team

### Step-by-step

**Step 1:** Create account

Create account on https://app.memu.so

Then, go to https://app.memu.so/api-key/ for generating api-keys.

**Step 2:** Add three lines to your code
```python
pip install memu-py

# Example usage
from memu import MemuClient
```

**Step 3:** Quick Start
```python
# Initialize
memu_client = MemuClient(
    base_url="https://api.memu.so", 
    api_key=os.getenv("MEMU_API_KEY")
)
memu_client.memorize_conversation(
    conversation=conversation_text, # Recommend longer conversation (~8000 tokens), see https://memu.pro/blog/memu-best-practice for details
    user_id="user001", 
    user_name="User", 
    agent_id="assistant001", 
    agent_name="Assistant"
)
```
Check [API reference](docs/API_REFERENCE.md) or [our blog](https://memu.pro/blog) for more details. 

📖 **See [`example/client/memory.py`](example/client/memory.py) for complete integration details**

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

See [self hosting README](README.self_host.md)

---


## ✨ Key Features

### 🎥 Demo Video

<div align="left">
  <a href="https://www.youtube.com/watch?v=qZIuCoLglHs">
    <img src="https://img.youtube.com/vi/ueOe4ZPlZLU/maxresdefault.jpg" alt="MemU Demo Video" width="600">
  </a>
  <br>
  <em>Click to watch the MemU demonstration video</em>
</div>

---

### Memory as file system

#### **Organize** - Autonomous Memory File Management
Your memories are structured as intelligent folders managed by a memory agent. We do not do explicit modeling for memories. The memory agent automatically decides what to record, modify, or archive. Think of it as having a personal librarian who knows exactly how to organize your thoughts.

#### **Link** - Interconnected Knowledge Graph
Memories don't exist in isolation. Our system automatically creates meaningful connections between related memories, building a rich network of hyperlinked documents and transforming memory discovery from search into effortless recall.

#### **Evolve** - Continuous Self-Improvement
Even when offline, your memory agent keeps working. It generates new insights by analyzing existing memories, identifies patterns, and creates summary documents through self-reflection. Your knowledge base becomes smarter over time, not just larger.

#### **Never Forget** - Adaptive Forgetting Mechanism
The memory agent automatically prioritizes information based on usage patterns. Recently accessed memories remain highly accessible, while less relevant content is deprioritized or forgotten. This creates a personalized information hierarchy that evolves with your needs.

---

## 😺 Advantages

### Higher Memory Accuracy
MemU achieves 92.09% average accuracy in Locomo dataset across all reasoning tasks, significantly outperforming competitors. Technical Report will be published soon!

![Memory Accuracy Comparison](assets/benchmark.png)
<em>(1) Single-hop questions require answers based on a single session; (2) Multi-hop questions require synthesizing information from multiple different sessions; (3) Temporal reasoning questions can be answered through temporal reasoning and capturing time-related data cues within the conversation; (4) Open-domain knowledge questions can be answered by integrating a speaker’s provided information with external knowledge such as commonsense or world facts; </em>

### Fast Retrieval

We categorize important information into documents, and during retrieval, we only need to find the relevant document content, eliminating the need for extensive embedding searches for fragmented sentences.

### Low cost

We can process hundreds of conversation turns at once, eliminating the need for developers to repeatedly call memory functions, thus saving users from wasting tokens on multiple memory operations. See [best practice](https://memu.pro/blog/memu-best-practice).

---
## 🎓 **Use Cases**

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="assets/usecase/ai_companion-0000.jpg" width="150" height="200"><br>**AI Companion** | <img src="assets/usecase/ai_role_play-0000.jpg" width="150" height="200"><br>**AI Role Play** | <img src="assets/usecase/ai_ip-0000.png" width="150" height="200"><br>**AI IP Characters** | <img src="assets/usecase/ai_edu-0000.jpg" width="150" height="200"><br>**AI Education** |
| <img src="assets/usecase/ai_therapy-0000.jpg" width="150" height="200"><br>**AI Therapy** | <img src="assets/usecase/ai_robot-0000.jpg" width="150" height="200"><br>**AI Robot** | <img src="assets/usecase/ai_creation-0000.jpg" width="150" height="200"><br>**AI Creation** | More...|
---

## 🤝 Contributing

We build trust through open-source collaboration. Your creative contributions drive memU's innovation forward. Explore our GitHub issues and projects to get started and make your mark on the future of memU.

📋 **[Read our detailed Contributing Guide →](CONTRIBUTING.md)**


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
<a href="https://github.com/camel-ai/camel"><img src="https://avatars.githubusercontent.com/u/134388954?s=200&v=4" alt="Camel" height="40" style="margin: 10px;"></a>
<a href="https://github.com/eigent-ai/eigent"><img src="https://www.eigent.ai/nav/logo_icon.svg" alt="Eigent" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="bytebase" height="40" style="margin: 10px;"></a>
</div>

---

*Interested in partnering with MemU? Contact us at [contact@nevamind.ai](mailto:contact@nevamind.ai)*

---

## 📱 Join Our WeChat Community

Connect with us on WeChat for the latest updates, community discussions, and exclusive content:

<div align="center">
<img src="assets/qrcode.png" alt="MemU WeChat and discord QR Code" width="480" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px;">


*Scan any of the QR codes above to join our WeChat community*

</div>

---

*Stay connected with the MemU community! Join our WeChat groups for real-time discussions, technical support, and networking opportunities.*


## Questionnaire

Help us improve! Share your feedback on our 3-min survey and get 30 free quota：https://forms.gle/H2ZuZVHv72xbqjvd7
