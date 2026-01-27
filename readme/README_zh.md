![MemU Banner](../assets/banner.png)

<div align="center">

# MemU

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

MemU 是一个 **7×24 全天候主动记忆框架**，能够持续学习、预测需求并自适应演化。它将被动的 LLM 后端转变为拥有**始终在线记忆**的智能代理，主动呈现洞察、预测需求，无需显式查询即可演化上下文。

---

## ⭐️ 给项目点个星

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
如果你觉得 MemU 有用或有趣，请给项目点个星 ⭐️，这将是对我们最大的支持！

---

## ✨ 核心能力

| 能力 | 描述 |
|------|------|
| 🔄 **持续学习** | 7×24 从每次交互中提取记忆——对话、文档、操作 |
| 🎯 **主动检索** | 在被询问之前预测信息需求，自动呈现相关上下文 |
| 🧠 **上下文演化** | 记忆结构根据使用模式和新兴主题实时适应 |
| 🔍 **双重智能** | 快速的嵌入式检索 + 深度 LLM 推理，实现全面理解 |
| 🎨 **多模态感知** | 跨文本、图像、音频、视频的统一记忆——记住所见所闻 |

---

## 🔄 主动记忆工作原理

与等待查询的传统检索系统不同，MemU 以**持续模式**运行：

### 被动记忆 vs 主动记忆

| 传统 RAG | MemU 主动记忆 |
|----------|---------------|
| ❌ 等待显式查询 | ✅ 持续监控上下文 |
| ❌ 被动信息检索 | ✅ 预测信息需求 |
| ❌ 静态知识库 | ✅ 自演化记忆结构 |
| ❌ 一次性处理 | ✅ 始终在线学习管道 |

### 主动记忆生命周期
```
┌─────────────────────────────────────────────────┐
│  1. 持续摄入                                     │
│  └─ 每次对话、文档、操作                          │
│     自动 7×24 处理                               │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  2. 实时提取                                     │
│  └─ 即时创建记忆条目                              │
│     无批处理延迟，即时可用                         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  3. 主动结构化                                   │
│  └─ 自动分类到演化主题                            │
│     层次化组织随使用适应                          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  4. 预期性检索                                   │
│  └─ 无需提示即呈现相关记忆                        │
│     上下文感知的建议和洞察                        │
└─────────────────────────────────────────────────┘
```

---

## 🎯 主动应用场景

### 1. **上下文助手** 
*智能体监控对话上下文并主动呈现相关记忆*
```python
# 用户开始讨论某个话题
用户: "我在考虑那个项目..."

# MemU 无需显式查询自动检索:
- 之前的项目讨论
- 相关偏好和约束
- 过去的决策及其结果
- 相关文档和资源

智能体: "根据您之前在仪表板重新设计方面的工作，
        我注意到您更喜欢 Material UI 组件..."
```

### 2. **预测性准备**
*智能体根据模式预测即将到来的需求*
```python
# 早晨例程检测
用户在上午 9 点登录（通常时间）

# MemU 主动呈现:
- 每日站会讨论要点
- 隔夜通知摘要
- 基于过去行为的优先任务
- 昨天工作的相关上下文

智能体: "早上好！以下是今天的相关内容..."
```

### 3. **自主记忆管理**
*系统无需手动干预自行组织*
```python
# 随着交互积累:
✓ 自动为新兴主题创建新类别
✓ 跨模态整合相关记忆
✓ 识别模式并提取更高层次的洞察
✓ 在保留历史的同时清理过时信息

# 结果: 始终优化的记忆结构
```

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
