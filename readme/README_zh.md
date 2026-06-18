![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### 文件系统即记忆，记忆塑造智能体

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU 是面向 AI 智能体的**记忆文件系统**。

memU 不会把智能体学到的一切压扁进一个巨大的 prompt 或一团不透明的向量里，而是像你管理电脑一样组织记忆——一棵可浏览、人类可读的 Markdown 文件树：

- **`MEMORY.md`** —— 智能体的活记忆：用户是谁、其偏好、目标，以及从每个来源中提取出的事件
- **`SKILL.md`** —— 学到的技能与工具模式：什么有效、应避免什么，以及如何重复执行常见任务
- **`INDEX.md`** —— 目录索引：覆盖每个记忆文件的可导航地图，让智能体在读取之前先知道该去哪里找
- **智能体读写这些文件**——它通过 `memorize()` 把新来源写入其中，通过 `retrieve()` 按需仅读取真正相关的片段

```txt
memory/
├── INDEX.md              ← 全局地图：类别、文件与摘要
├── MEMORY.md             ← 画像、偏好、目标与关键事件
└── skill/
    ├── {skill_name}/
    │   └── SKILL.md       ← 一项学到的技能或工具模式
    └── {another_skill}/
        └── SKILL.md
```

**文件系统即记忆**：一个层级化、可浏览的界面，每条记忆都能追溯回它的来源。
**记忆塑造智能体**：因为这个界面是结构化且自组织的，它不再是被动的存储，而成为塑造智能体如何思考与行动的那一层。

---

## 🔄 工作原理

可以把它看成两个文件系统操作：把原始来源**写入**有组织的记忆，再把正确的文件**读回**给智能体。

```
WRITE — memorize()                                         READ — retrieve()
──────────────────────────────────────────────            ──────────────────────────────────────────────
raw files        →  extract  →  files + folders            query  →  walk folders  →  ranked files
─────────────       ─────────    ──────────────            ─────     ────────────     ─────────────
chat logs        →  parse    →  profile / event items      user / task query
documents / URLs →  facts    →  knowledge / skill items       │
images / video   →  caption  →  resources + summaries         ├─ route + scope    → relevant folders (categories)
audio            →  transcribe→ event / knowledge items       ├─ rank by relevance → matching files (items)
tool logs        →  mine      → tool / skill items            └─ trace to source   → original resources
```

**写入文件系统（`memorize`）**

1. **摄入（Ingest）** — 把每个来源作为一个 `Resource`（原始文件）存下，记录其模态与来源位置
2. **预处理（Preprocess）** — 解析文本、为图片/视频生成描述、转写音频，并规范化输入
3. **提取（Extract）** — 把原始内容转成带类型的 `MemoryItem`（文件）：profile、event、knowledge、behavior、skill 或 tool 记忆
4. **组织（Organize）** — 把记忆项归入 `MemoryCategory` 文件夹，交叉关联、向量化，并汇总成可浏览的树
5. **持久化（Persist）** — 通过所配置的后端写入记录、关系、向量与文件夹摘要

**从文件系统读取（`retrieve`）**

6. **检索（Retrieve）** — 在文件夹中导航，仅返回与当前用户、智能体、会话或任务相关的文件

---

## 🗂️ 记忆文件系统

memU 的主要产出是一棵可浏览的记忆树——文件夹、文件，以及它们背后的来源素材——通过仓储契约持久化，并以字典形式从 `memorize()` 和 `retrieve()` 返回。

```txt
MemoryCategory                       ← 文件夹：带演进式摘要的主题
├── name, description, summary
├── embedding
└── MemoryItem[]                     ← 文件：带类型的原子记忆
    ├── memory_type: profile | event | knowledge | behavior | skill | tool
    ├── summary, extra, happened_at, embedding
    └── Resource                     ← 来源：这条记忆所来自的原始文件
        └── url, modality, local_path, caption, embedding
```

| 记录 | 文件系统角色 | 用途 |
|--------|------------------|---------|
| `MemoryCategory` | **文件夹** — 归集相关记忆并维护主题级摘要 | 为宽泛查询加载紧凑上下文 |
| `MemoryItem` | **文件** — 带类型的原子记忆，含摘要与可选元数据 | 注入精确的事实、偏好、事件、技能与工具模式 |
| `Resource` | **来源素材** — 记忆背后的原始文件，附带描述/文本 | 把上下文追溯回它的来源 |
| `CategoryItem` | **链接** — 把记忆项归档到文件夹下的边 | 在不重新处理来源的情况下导航相关记忆 |

这为智能体提供了一个稳定的记忆文件系统：原始来源只需摄入一次，之后便可请求限定范围、经过排序的文件，而无需重读每一份来源素材。

---

## 🧩 memU 构建了什么

文件系统的每一层都以结构化记录的形式存储：

| 层 | 代表什么 | 智能体为何使用 |
|-------|--------------------|-------------------|
| **MemoryCategory** | 自动生成的文件夹：带演进式摘要的主题 | 先加载高层上下文，再深入细节 |
| **MemoryItem** | 文件：带类型与摘要的原子结构化记忆 | 注入精确的事实、偏好、事件、技能与工具模式 |
| **Resource** | 文件背后的来源素材：对话、文档、图片、视频、音频、URL 或文件 | 把记忆追溯回其来源 |
| **CategoryItem** | 把记忆项归档到文件夹下的链接 | 在不重新处理来源的情况下导航相关记忆 |
| **Embedding** | 覆盖文件夹、文件与来源的向量索引 | 以低延迟检索相关上下文 |

`memorize()` 输出示例：

```json
{
  "resource": {
    "id": "res_01",
    "url": "files/launch-meeting.mp4",
    "modality": "video",
    "caption": "A product planning discussion about onboarding and launch risks."
  },
  "items": [
    {
      "id": "mem_01",
      "memory_type": "event",
      "summary": "The team decided to simplify onboarding before the next launch review."
    },
    {
      "id": "mem_02",
      "memory_type": "profile",
      "summary": "The user prefers concise implementation plans with explicit verification steps."
    },
    {
      "id": "mem_03",
      "memory_type": "tool",
      "summary": "Use repository-wide search before editing configuration files to avoid missing duplicated settings."
    }
  ],
  "categories": [
    {
      "id": "cat_01",
      "name": "product_goals",
      "summary": "Current launch priorities, onboarding decisions, and unresolved risks."
    }
  ],
  "relations": [
    { "item_id": "mem_01", "category_id": "cat_01" }
  ]
}
```

随后，智能体可以调用 `retrieve()` 获取一份限定范围、经过排序的上下文负载：

```python
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What context matters for this launch task?"}}],
    where={"user_id": "123"},
)
```

---

## ⭐️ 给仓库点个 Star

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

如果你觉得 memU 有用或有意思，欢迎在 GitHub 上点一个 Star ⭐️，我们将不胜感激。

---

## ✨ 核心特性

| 能力 | 说明 |
|------------|-------------|
| 🗂️ **多模态摄入** | 把对话、文档、图片、视频、音频、URL、日志与本地文件写入记忆 |
| 📁 **记忆文件系统** | 持久化文件夹（类别）、文件（记忆项）、来源素材、链接、摘要与向量 |
| 🧠 **带类型的记忆提取** | 从原始来源提取 profile、event、knowledge、behavior、skill 与 tool 记忆 |
| 🧭 **自组织文件夹** | 自动构建类别、链接、摘要与向量，无需手工打标签 |
| 🤖 **面向智能体的检索** | 读取限定范围、经过排序的上下文，可注入任意智能体工作流 |
| 🧱 **可插拔存储** | 使用 in-memory、SQLite 或 Postgres 后端，共享同一套仓储契约 |
| 🔀 **基于 Profile 的 LLM 路由** | 通过可配置的 LLM profile 路由对话、向量、视觉与转写任务 |

---

## 🎯 应用场景

### 1. **对话记忆**
*把聊天记录转化为用户偏好、目标、事件与关系上下文。*

```python
await service.memorize(
    resource_url="examples/resources/conversations/conv1.json",
    modality="conversation",
    user={"user_id": "123"},
)

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What should I remember about this user?"}}],
    where={"user_id": "123"},
)
```

### 2. **面向编码智能体的工作区上下文**
*把文档、PR 说明、日志与设计决策转化为可复用的项目记忆。*

```python
await service.memorize(resource_url="docs/architecture.md", modality="document")
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "How should I structure this module?"}}],
)
```

### 3. **多模态知识层**
*从文档、截图、图片、视频与语音笔记中提取可检索的事实。*

```python
await service.memorize(resource_url="examples/resources/docs/doc1.txt", modality="document")
await service.memorize(resource_url="examples/resources/images/image1.png", modality="image")
# Audio is supported for your own .mp3/.wav/.m4a files.
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **工具与智能体学习**
*把执行轨迹转化为工具记忆，告诉未来的智能体何时使用某个工具、应避免哪些错误。*

```python
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ 架构

记忆文件系统既层级化到足以浏览，又结构化到足以直接检索：

<img width="100%" alt="structure" src="../assets/structure.png" />

| 层 | 主要职责 | 检索职责 |
|-------|--------------|----------------|
| **Category（文件夹）** | 维护主题级摘要 | 为宽泛查询组装紧凑上下文 |
| **Item（文件）** | 存储带类型的原子记忆 | 加载精确的事实、事件、偏好、技能与工具模式 |
| **Resource（来源）** | 保留来源素材与描述 | 当记忆项/类别摘要不够时召回原始上下文 |

关于 `MemoryService`、工作流流水线、存储后端与 LLM 路由的运行时视图，参见 [docs/architecture.md](../docs/architecture.md)。

---

## 🚀 快速开始

### 方式一：云端版本

👉 **[memu.so](https://memu.so)** — 托管 API，提供托管式摄入、结构化记忆与检索

企业部署请联系：**info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer <token>` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | 摄入原始数据并构建结构化记忆 |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | 查询处理状态 |
| `POST` | `/api/v3/memory/categories` | 列出自动生成的类别 |
| `POST` | `/api/v3/memory/retrieve` | 查询记忆以获取智能体上下文 |

📚 **[完整 API 文档](https://memu.pro/docs#cloud-version)**

---

### 方式二：自托管

#### 安装

从本仓库的克隆中安装：

```bash
uv sync
# 或者，进行完整的开发环境安装：
make install
```

或者安装已发布的包：

```bash
pip install memu-py
```

> **环境要求**：Python 3.13+。默认示例使用 OpenAI，请设置 `OPENAI_API_KEY`，或通过 `llm_profiles` 传入其它提供方。

**运行内存模式冒烟脚本：**
```bash
export OPENAI_API_KEY=your_key
cd tests
uv run python test_inmemory.py
```

**使用 PostgreSQL + pgvector 运行：**
```bash
uv sync --extra postgres
docker run -d --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

export OPENAI_API_KEY=your_key
export POSTGRES_DSN=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/memu
cd tests
uv run python test_postgres.py
```

---

### 自定义 LLM 与 Embedding 提供方

```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"
        },
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
)
```

---

### OpenRouter 集成

```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_key",
            "chat_model": "anthropic/claude-3.5-sonnet",
            "embed_model": "openai/text-embedding-3-small",
        },
    },
    database_config={"metadata_store": {"provider": "inmemory"}},
)
```

---

## 📖 核心 API

### `memorize()` — 结构化原始数据

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",    # 本地文件路径或 HTTP URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # 可选：限定到某个用户或智能体
)
# 处理完成后返回：
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- 把原始输入转换为带类型的记忆项
- 自动对记忆项分类并向量化，无需手工打标签
- 保留来源资源以及记忆项—类别关系

---

### `retrieve()` — 加载智能体上下文

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

```python
# 检索策略在服务上通过 retrieve_config 一次性设定：
#   MemoryService(retrieve_config={"method": "rag"})   # 向量优先召回
#   MemoryService(retrieve_config={"method": "llm"})   # LLM 排序召回
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # 范围过滤
)
# 返回：
# {
#   "needs_retrieval": true,
#   "original_query": "...",
#   "rewritten_query": "...",
#   "next_step_query": "...",
#   "categories": [...],
#   "items": [...],
#   "resources": [...]
# }
```

| `retrieve_config.method` | 行为 | 成本 | 适用场景 |
|--------------------------|----------|------|----------|
| `rag` | 向量优先的类别/记忆项/资源召回，默认启用可选的 LLM 路由与充分性检查 | 向量调用加 LLM 调用，除非关闭 `route_intention` 与 `sufficiency_check` | 可控推理下的快速限定召回 |
| `llm` | 由 LLM 排序的类别/记忆项/资源召回 | 每一层都进行 LLM 排序 | 更深的语义排序 |

---

## 💡 示例工作流

### 持续学习的助手
```bash
export OPENAI_API_KEY=your_key
uv run python examples/example_1_conversation_memory.py
```
自动提取偏好、构建关系模型，并在未来对话中浮现相关上下文。

### 自我改进的智能体
```bash
uv run python examples/example_2_skill_extraction.py
```
监控智能体的行为，识别成功与失败中的模式，从经验中自动生成技能指南。

### 多模态上下文构建器
```bash
uv run python examples/example_3_multimodal_memory.py
```
自动交叉关联文本、图片与文档，汇入统一的记忆层。

---

## 📊 性能

memU 在 Locomo 基准的所有推理任务上取得了 **92.09% 的平均准确率**。

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

查看详细结果：[memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 生态

| 仓库 | 说明 |
|------------|-------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | 核心记忆文件系统 —— 摄入、提取、检索 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | 带实时同步与 webhook 触发的后端 |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | 用于浏览与监控记忆的可视化面板 |

**快速链接：**
- 🚀 [试用 MemU Cloud](https://app.memu.so/quick-start)
- 📚 [API 文档](https://memu.pro/docs)
- 💬 [Discord 社区](https://discord.com/invite/hQZntfGsbJ)

---

## 🤝 合作伙伴

<div align="center">

<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://openagents.org"><img src="../assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Milvus" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="../assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="../assets/partners/jazz.png" alt="Jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="../assets/partners/buddie.png" alt="Buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="../assets/partners/bytebase.png" alt="Bytebase" height="40" style="margin: 10px;"></a>
<a href="https://github.com/LazyAGI/LazyLLM"><img src="../assets/partners/LazyLLM.png" alt="LazyLLM" height="40" style="margin: 10px;"></a>
<a href="https://clawdchat.ai/"><img src="../assets/partners/Clawdchat.png" alt="Clawdchat" height="40" style="margin: 10px;"></a>

</div>

---

## 🤝 贡献

```bash
# Fork 并克隆
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 安装开发依赖
make install

# 提交前运行质量检查
make check
```

完整指南参见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

**前置条件：** Python 3.13+、[uv](https://github.com/astral-sh/uv)、Git

---

## 📄 许可证

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 社区

- **GitHub Issues**：[报告 bug 与提交功能请求](https://github.com/NevaMind-AI/memU/issues)
- **Discord**：[加入社区](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**：[关注 @memU_ai](https://x.com/memU_ai)
- **联系**：info@nevamind.ai

---

<div align="center">

⭐ **在 GitHub 上给我们点 Star**，第一时间获取新版本通知！

</div>
