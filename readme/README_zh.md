![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### 面向 AI 智能体的全天候主动记忆系统

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU 是一个专为 **24/7 主动智能体**打造的记忆框架。
它专为长时间运行设计，能够大幅**降低保持智能体始终在线的 LLM token 成本**，使持续运行、不断进化的智能体在生产系统中变得切实可行。
memU **持续捕获并理解用户意图**。即使没有明确指令，智能体也能判断你即将要做什么并主动执行。

---

## 🤖 [OpenClaw (Moltbot, Clawdbot) Alternative](https://memu.bot)

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/memUbot.png" />

- **Download-and-use and simple** to get started.
- Builds long-term memory to **understand user intent** and act proactively.
- **Cuts LLM token cost** with smaller context.

Try now: [memU bot](https://memu.bot)

---

## 🗃️ 记忆即文件系统，文件系统即记忆

memU 将**记忆视为文件系统**——结构化、层次化、即时可访问。

| 文件系统 | memU 记忆 |
|---------|----------|
| 📁 文件夹 | 🏷️ 类别（自动组织的主题） |
| 📄 文件 | 🧠 记忆条目（提取的事实、偏好、技能） |
| 🔗 符号链接 | 🔄 交叉引用（关联的记忆相互链接） |
| 📂 挂载点 | 📥 资源（对话、文档、图像） |

**为何重要：**
- **像浏览目录一样导航记忆**——从宽泛的类别深入到具体的事实
- **即时挂载新知识**——对话和文档成为可查询的记忆
- **万物互联**——记忆相互引用，构建连接的知识图谱
- **持久化且可迁移**——像文件一样导出、备份和迁移记忆

```
memory/
├── preferences/
│   ├── communication_style.md
│   └── topic_interests.md
├── relationships/
│   ├── contacts/
│   └── interaction_history/
├── knowledge/
│   ├── domain_expertise/
│   └── learned_skills/
└── context/
    ├── recent_conversations/
    └── pending_tasks/
```

正如文件系统将原始字节转化为有组织的数据，memU 将原始交互转化为**结构化、可搜索、主动式的智能**。

---

## ⭐️ 给项目点个星

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
如果你觉得 memU 有用或有趣，请给项目点个星 ⭐️，这将是对我们最大的支持！

---


## ✨ 核心能力

| 能力 | 描述 |
|------|------|
| 🤖 **24/7 主动智能体** | 始终在线的记忆智能体，在后台持续工作——永不休眠，永不遗忘 |
| 🎯 **用户意图捕获** | 自动理解并记住用户在各个会话中的目标、偏好和上下文 |
| 💰 **成本高效** | 通过缓存洞察和避免冗余 LLM 调用来降低长期运行的 token 成本 |
---

## 🔄 主动记忆工作原理

```bash

cd examples/proactive
python proactive.py

```

---

### Proactive Memory Lifecycle
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         USER QUERY                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                 │                                                           │
                 ▼                                                           ▼
┌────────────────────────────────────────┐         ┌────────────────────────────────────────────────┐
│         🤖 MAIN AGENT                  │         │              🧠 MEMU BOT                       │
│                                        │         │                                                │
│  Handle user queries & execute tasks   │  ◄───►  │  Monitor, memorize & proactive intelligence   │
├────────────────────────────────────────┤         ├────────────────────────────────────────────────┤
│                                        │         │                                                │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  1. RECEIVE USER INPUT           │  │         │  │  1. MONITOR INPUT/OUTPUT                 │  │
│  │     Parse query, understand      │  │   ───►  │  │     Observe agent interactions           │  │
│  │     context and intent           │  │         │  │     Track conversation flow              │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  2. PLAN & EXECUTE               │  │         │  │  2. MEMORIZE & EXTRACT                   │  │
│  │     Break down tasks             │  │   ◄───  │  │     Store insights, facts, preferences   │  │
│  │     Call tools, retrieve data    │  │  inject │  │     Extract skills & knowledge           │  │
│  │     Generate responses           │  │  memory │  │     Update user profile                  │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  3. RESPOND TO USER              │  │         │  │  3. PREDICT USER INTENT                  │  │
│  │     Deliver answer/result        │  │   ───►  │  │     Anticipate next steps                │  │
│  │     Continue conversation        │  │         │  │     Identify upcoming needs              │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  4. LOOP                         │  │         │  │  4. RUN PROACTIVE TASKS                  │  │
│  │     Wait for next user input     │  │   ◄───  │  │     Pre-fetch relevant context           │  │
│  │     or proactive suggestions     │  │  suggest│  │     Prepare recommendations              │  │
│  └──────────────────────────────────┘  │         │  │     Update todolist autonomously         │  │
│                                        │         │  └──────────────────────────────────────────┘  │
└────────────────────────────────────────┘         └────────────────────────────────────────────────┘
                 │                                                           │
                 └───────────────────────────┬───────────────────────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │     CONTINUOUS SYNC LOOP     │
                              │  Agent ◄──► MemU Bot ◄──► DB │
                              └──────────────────────────────┘
```

---

## 🎯 主动应用场景

### 1. **信息推荐**
*智能体监控用户兴趣，主动呈现相关内容*
```python
# 用户一直在研究 AI 话题
MemU 追踪：阅读历史、收藏文章、搜索查询

# 当新内容到达时：
智能体："我发现了 3 篇关于 RAG 优化的新论文，与你最近关于检索系统的
        研究方向一致。其中一位作者（陈博士）你之前引用过，昨天发表了新作。"

# 主动行为：
- 从浏览模式学习话题偏好
- 追踪作者/来源可信度偏好
- 基于参与历史过滤噪音
- 选择最佳时机进行推荐
```

### 2. **邮件管理**
*智能体学习沟通模式，处理日常通信*
```python
# MemU 随时间观察邮件模式：
- 常见场景的回复模板
- 优先联系人和紧急关键词
- 日程偏好和可用时间
- 写作风格和语气变化

# 主动邮件助理：
智能体："你有 12 封新邮件。我已为 3 个常规请求起草了回复，
        并标记了来自优先联系人的 2 个紧急事项。
        需要我根据约翰提到的冲突重新安排明天的会议吗？"

# 自主执行：
✓ 起草上下文感知的回复
✓ 分类并排序收件箱
✓ 检测日程冲突
✓ 总结长对话线程的关键决策
```

### 3. **交易与财务监控**
*智能体追踪市场情况和用户投资行为*
```python
# MemU 学习交易偏好：
- 从历史决策中了解风险承受能力
- 偏好的行业和资产类别
- 对市场事件的响应模式
- 投资组合再平衡触发条件

# 主动提醒：
智能体："NVDA 盘后下跌 5%。根据你的历史行为，
        你通常在科技股跌幅超过 3% 时买入。
        你当前的配置允许增加 $2,000 的敞口，
        同时保持你 70/30 的股债目标。"

# 持续监控：
- 追踪与用户定义阈值相关的价格警报
- 关联新闻事件与投资组合影响
- 从已执行与忽略的建议中学习
- 预判税损收割机会
```


...

---

## 🗂️ 分层记忆架构

MemU 的三层系统同时支持**响应式查询**和**主动上下文加载**：

<img width="100%" alt="structure" src="../assets/structure.png" />

| 层级 | 响应式使用 | 主动使用 |
|------|-----------|----------|
| **资源层** | 直接访问原始数据 | 后台监控新模式 |
| **条目层** | 针对性事实检索 | 从进行中的交互实时提取 |
| **类别层** | 摘要级概览 | 自动上下文组装以进行预测 |

**主动优势：**
- **自动分类**：新记忆自组织到主题中
- **模式检测**：系统识别重复出现的主题
- **上下文预测**：预测接下来需要什么信息

---

## 🚀 快速开始

### 选项 1：云版本

立即体验主动记忆：

👉 **[memu.so](https://memu.so)** - 提供 7×24 持续学习的托管服务

如需具有自定义主动工作流的企业部署，请联系 **info@nevamind.ai**

#### 云 API (v3)

| 基础 URL | `https://api.memu.so` |
|----------|----------------------|
| 认证 | `Authorization: Bearer YOUR_API_KEY` |

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/v3/memory/memorize` | 注册持续学习任务 |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | 检查实时处理状态 |
| `POST` | `/api/v3/memory/categories` | 列出自动生成的类别 |
| `POST` | `/api/v3/memory/retrieve` | 查询记忆（支持主动上下文加载） |

📚 **[完整 API 文档](https://memu.pro/docs#cloud-version)**

---

### 选项 2：自托管

#### 安装
```bash
pip install -e .
```

#### 基础示例

> **要求**：Python 3.13+ 和 OpenAI API 密钥

**测试持续学习**（内存模式）：
```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**测试持久化存储**（PostgreSQL）：
```bash
# 启动带 pgvector 的 PostgreSQL
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 运行持续学习测试
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

两个示例都演示了**主动记忆工作流**：
1. **持续摄入**：顺序处理多个文件
2. **自动提取**：即时创建记忆
3. **主动检索**：上下文感知的记忆呈现

查看 [`tests/test_inmemory.py`](../tests/test_inmemory.py) 和 [`tests/test_postgres.py`](../tests/test_postgres.py) 了解实现细节。

---

### 自定义 LLM 和嵌入提供者

MemU 支持 OpenAI 以外的自定义 LLM 和嵌入提供者。通过 `llm_profiles` 配置：
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        # LLM 操作的默认配置
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_api_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk" 或 "http"
        },
        # 嵌入的单独配置
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_voyage_api_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... 其他配置
)
```

---

### OpenRouter 集成

MemU 支持 [OpenRouter](https://openrouter.ai) 作为模型提供者，让您通过单个 API 访问多个 LLM 提供者。

#### 配置
```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_openrouter_api_key",
            "chat_model": "anthropic/claude-3.5-sonnet",  # 任何 OpenRouter 模型
            "embed_model": "openai/text-embedding-3-small",  # 嵌入模型
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
    },
)
```

#### 环境变量

| 变量 | 描述 |
|------|------|
| `OPENROUTER_API_KEY` | 您的 OpenRouter API 密钥，来自 [openrouter.ai/keys](https://openrouter.ai/keys) |

#### 支持的功能

| 功能 | 状态 | 备注 |
|------|------|------|
| 聊天补全 | 支持 | 适用于任何 OpenRouter 聊天模型 |
| 嵌入 | 支持 | 通过 OpenRouter 使用 OpenAI 嵌入模型 |
| 视觉 | 支持 | 使用支持视觉的模型（如 `openai/gpt-4o`） |

#### 运行 OpenRouter 测试
```bash
export OPENROUTER_API_KEY=your_api_key

# 完整工作流测试（记忆 + 检索）
python tests/test_openrouter.py

# 嵌入专项测试
python tests/test_openrouter_embedding.py

# 视觉专项测试
python tests/test_openrouter_vision.py
```

查看 [`examples/example_4_openrouter_memory.py`](../examples/example_4_openrouter_memory.py) 获取完整示例。

---

## 📖 核心 API

### `memorize()` - 持续学习管道

实时处理输入并立即更新记忆：

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # 文件路径或 URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # 可选：限定到特定用户
)

# 立即返回提取的记忆:
{
    "resource": {...},      # 存储的资源元数据
    "items": [...],         # 提取的记忆条目（即时可用）
    "categories": [...]     # 自动更新的类别结构
}
```

**主动功能：**
- 零延迟处理——记忆即时可用
- 无需手动标记的自动分类
- 与现有记忆交叉引用以检测模式

### `retrieve()` - 双模式智能

MemU 同时支持**主动上下文加载**和**响应式查询**：

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

#### 基于 RAG 的检索 (`method="rag"`)

使用嵌入的快速**主动上下文组装**：

- ✅ **即时上下文**：亚秒级记忆呈现
- ✅ **后台监控**：可持续运行而无 LLM 成本
- ✅ **相似度评分**：自动识别最相关的记忆

#### 基于 LLM 的检索 (`method="llm"`)

针对复杂上下文的深度**预期性推理**：

- ✅ **意图预测**：LLM 在用户询问之前推断需求
- ✅ **查询演化**：随着上下文发展自动优化搜索
- ✅ **提前终止**：收集到足够上下文时停止

#### 对比

| 方面 | RAG（快速上下文） | LLM（深度推理） |
|------|------------------|----------------|
| **速度** | ⚡ 毫秒级 | 🐢 秒级 |
| **成本** | 💰 仅嵌入 | 💰💰 LLM 推理 |
| **主动使用** | 持续监控 | 触发式上下文加载 |
| **最适合** | 实时建议 | 复杂预测 |

#### 使用
```python
# 带上下文历史的主动检索
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "他们的偏好是什么？"}},
        {"role": "user", "content": {"text": "告诉我工作习惯"}}
    ],
    where={"user_id": "123"},  # 可选：范围过滤
    method="rag"  # 或 "llm" 用于更深入的推理
)

# 返回上下文感知的结果:
{
    "categories": [...],     # 相关主题领域（自动优先排序）
    "items": [...],          # 具体记忆事实
    "resources": [...],      # 原始来源以供追溯
    "next_step_query": "..." # 预测的后续上下文
}
```

**主动过滤**：使用 `where` 限定持续监控范围：
- `where={"user_id": "123"}` - 用户特定上下文
- `where={"agent_id__in": ["1", "2"]}` - 多智能体协调
- 省略 `where` 以获取全局上下文感知

> 📚 **完整 API 文档**，请参阅 [SERVICE_API.md](../docs/SERVICE_API.md) - 包含主动工作流模式、管道配置和实时更新处理。

---

## 💡 主动场景

### 示例 1：始终学习的助手

无需显式记忆命令，从每次交互中持续学习：
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**主动行为：**
- 从随意提及中自动提取偏好
- 从交互模式构建关系模型
- 在未来对话中呈现相关上下文
- 根据学习的偏好调整沟通风格

**最适合：** 个人 AI 助手、记住用户的客户支持、社交聊天机器人

---

### 示例 2：自我改进的智能体

从执行日志中学习并主动建议优化：
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**主动行为：**
- 持续监控智能体操作和结果
- 识别成功和失败中的模式
- 从经验中自动生成技能指南
- 主动为类似的未来任务建议策略

**最适合：** DevOps 自动化、智能体自我改进、知识捕获

---

### 示例 3：多模态上下文构建器

将不同输入类型的记忆统一为全面的上下文：
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**主动行为：**
- 自动交叉引用文本、图像和文档
- 跨模态构建统一理解
- 讨论相关话题时呈现视觉上下文
- 通过组合多个来源预测信息需求

**最适合：** 文档系统、学习平台、研究助手

---

## 📊 性能表现

MemU 在 Locomo 基准测试中，在所有推理任务上实现了 **92.09% 的平均准确率**，展示了可靠的主动记忆操作。

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

查看详细实验数据：[memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 生态系统

| 仓库 | 描述 | 主动功能 |
|------|------|----------|
| **[memU](https://github.com/NevaMind-AI/memU)** | 核心主动记忆引擎 | 7×24 学习管道、自动分类 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | 带持续同步的后端 | 实时记忆更新、webhook 触发 |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | 可视化记忆仪表板 | 实时记忆演化监控 |

**快速链接：**
- 🚀 [试用 MemU 云服务](https://app.memu.so/quick-start)
- 📚 [API 文档](https://memu.pro/docs)
- 💬 [Discord 社区](https://discord.gg/memu)

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

</div>

---

## 🤝 如何贡献

我们欢迎社区的各种贡献！无论是修复错误、添加功能还是改进文档，您的帮助都将受到赞赏。

### 开始贡献

要开始为 MemU 做贡献，您需要设置开发环境：

#### 先决条件
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（Python 包管理器）
- Git

#### 设置开发环境
```bash
# 1. Fork 并克隆仓库
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 2. 安装开发依赖
make install
```

`make install` 命令将：
- 使用 `uv` 创建虚拟环境
- 安装所有项目依赖
- 设置代码质量检查的 pre-commit hooks

#### 运行质量检查

在提交贡献之前，请确保您的代码通过所有质量检查：
```bash
make check
```

`make check` 命令运行：
- **锁文件验证**：确保 `pyproject.toml` 一致性
- **Pre-commit hooks**：使用 Ruff 检查代码，使用 Black 格式化
- **类型检查**：运行 `mypy` 进行静态类型分析
- **依赖分析**：使用 `deptry` 查找过时的依赖项

### 贡献指南

有关详细的贡献指南、代码标准和开发实践，请参阅 [CONTRIBUTING.md](../CONTRIBUTING.md)。

**快速提示：**
- 为每个功能或错误修复创建新分支
- 编写清晰的提交信息
- 为新功能添加测试
- 根据需要更新文档
- 推送前运行 `make check`

---

## 📄 许可证

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 社区

- **GitHub Issues**：[报告错误和请求功能](https://github.com/NevaMind-AI/memU/issues)
- **Discord**：[加入社区](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**：[关注 @memU_ai](https://x.com/memU_ai)
- **联系方式**：info@nevamind.ai

---

<div align="center">

⭐ **在 GitHub 上给我们点星**，获取新版本通知！

</div>
