![MemU Banner](assets/banner.png)

<div align="center">

# MemU

### 面向未来的智能体记忆系统

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</div>

---

## 📖 项目概述

MemU 是一个面向 LLM 和 AI 智能体的记忆框架。它接收**多模态输入**（对话、文档、图像），将其提取为结构化记忆，并组织成**分层文件系统**，支持**基于嵌入的检索（RAG）** 和**非嵌入检索（LLM）**。

### 🎯 项目目标
- 为 AI 智能体提供长期、结构化的记忆能力
- 支持多模态内容的统一处理和管理
- 实现高效、智能的记忆检索和利用
- 构建可扩展、自演化的记忆系统

### 💡 核心价值
- **智能记忆管理**：将原始数据转化为有价值的记忆知识
- **多模态支持**：统一处理文本、图像、音频、视频等多种格式
- **双检索策略**：结合 RAG 的高效性和 LLM 的深度理解
- **自演化能力**：记忆结构根据使用模式自适应优化

---

## ⭐️ 给项目点个星

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
如果你觉得 MemU 有用或有趣，请给项目点个星 ⭐️，这将是对我们最大的支持！

---

## 🎉 2026 新年挑战赛

MemU 正在与四个开源项目合作举办 2026 新年挑战赛。🎉 在 1月8日-18日期间，贡献者可以向 MemU 提交 PR，赢取现金奖励、社区认可和平台积分。🎁 [了解更多并参与](https://discord.gg/KaWy6SBAsx)

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🗂️ **分层文件系统** | 三层架构：资源 → 条目 → 类别，支持完整追溯 |
| 🔍 **双检索方法** | RAG（基于嵌入）用于快速检索，LLM（非嵌入）用于深度语义理解 |
| 🎨 **多模态支持** | 处理对话、文档、图像、音频和视频 |
| 🔄 **自演化记忆** | 记忆结构根据使用模式自适应改进 |

---

## 🗂️ 分层文件系统

MemU 采用**三层架构**组织记忆，灵感来源于分层存储系统：

<img width="100%" alt="structure" src="assets/structure.png" />

| 层级 | 描述 | 示例 |
|------|------|------|
| **资源层** | 原始多模态数据仓库 | JSON 对话、文本文档、图像、视频 |
| **条目层** | 离散提取的记忆单元 | 个人偏好、技能、观点、习惯 |
| **类别层** | 聚合的文本记忆及摘要 | `preferences.md`、`work_life.md`、`relationships.md` |

**主要优势：**
- **完整追溯性**：从原始数据 → 条目 → 类别全程可追溯
- **渐进式摘要**：每层提供越来越抽象的视图
- **灵活组织**：类别根据内容模式演化

---

## 🎨 多模态支持

MemU 将多种内容类型处理为统一的记忆：

| 模态 | 输入 | 处理方式 |
|------|------|----------|
| `conversation` | JSON 聊天记录 | 提取偏好、观点、习惯、关系 |
| `document` | 文本文件 (.txt, .md) | 提取知识、技能、事实 |
| `image` | PNG、JPG 等图像 | 视觉模型提取视觉概念和描述 |
| `video` | 视频文件 | 帧提取 + 视觉分析 |
| `audio` | 音频文件 | 转录 + 文本处理 |

所有模态都统一到相同的三层层次结构中，实现跨模态检索。

---

## 🚀 快速开始

### 选项 1：云版本

无需任何设置，立即体验 MemU：

👉 **[memu.so](https://memu.so)** - 托管云服务，提供完整的 API 访问

如需企业部署和定制解决方案，请联系 **info@nevamind.ai**

#### 云 API (v3)

| 基础 URL | `https://api.memu.so` |
|----------|----------------------|
| 认证 | `Authorization: Bearer YOUR_API_KEY` |

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/v3/memory/memorize` | 注册记忆任务 |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | 获取任务状态 |
| `POST` | `/api/v3/memory/categories` | 列出记忆类别 |
| `POST` | `/api/v3/memory/retrieve` | 检索记忆（语义搜索） |

📚 **[完整 API 文档](https://memu.pro/docs#cloud-version)**

---

### 选项 2：自托管

#### 安装

```bash
pip install -e .
```

#### 基础示例

> **要求**：Python 3.13+ 和 OpenAI API 密钥

**使用内存存储测试**（无需数据库）：

```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**使用 PostgreSQL 存储测试**（需要 pgvector）：

```bash
# 启动带 pgvector 的 PostgreSQL
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 运行测试
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

两个示例都展示了完整的工作流程：
1. **记忆**：处理对话文件并提取结构化记忆
2. **检索 (RAG)**：基于嵌入的快速搜索
3. **检索 (LLM)**：深度语义理解搜索

查看 [`tests/test_inmemory.py`](tests/test_inmemory.py) 和 [`tests/test_postgres.py`](tests/test_postgres.py) 获取完整源代码。

---

### 自定义 LLM 和嵌入提供者

MemU 支持除 OpenAI 之外的自定义 LLM 和嵌入提供者。通过 `llm_profiles` 配置：

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

## 📖 核心 API

### `memorize()` - 提取和存储记忆

处理输入资源并提取结构化记忆：

<img width="100%" alt="memorize" src="assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # 文件路径或 URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # 可选：限定到特定用户
)

# 返回：
{
    "resource": {...},      # 存储的资源元数据
    "items": [...],         # 提取的记忆条目
    "categories": [...]     # 更新的类别摘要
}
```

### `retrieve()` - 查询记忆

基于查询检索相关记忆。MemU 支持**两种检索策略**：

<img width="100%" alt="retrieve" src="assets/retrieve.png" />

#### 基于 RAG 的检索 (`method="rag"`)

使用余弦相似度的快速**嵌入向量搜索**：
- ✅ **快速**：纯向量计算
- ✅ **可扩展**：适用于大型记忆存储
- ✅ **返回分数**：每个结果包含相似度分数

#### 基于 LLM 的检索 (`method="llm"`)

通过直接 LLM 推理的深度**语义理解**：
- ✅ **深度理解**：LLM 理解上下文和细微差别
- ✅ **查询重写**：在每个层级自动优化查询
- ✅ **自适应**：当找到足够信息时提前停止

#### 对比

| 方面 | RAG | LLM |
|------|-----|-----|
| **速度** | ⚡ 快速 | 🐢 较慢 |
| **成本** | 💰 低 | 💰💰 较高 |
| **语义深度** | 中等 | 深度 |
| **第二层范围** | 所有条目 | 仅相关类别中的条目 |
| **输出** | 带相似度分数 | 按 LLM 推理排序 |

两种方法都支持：
- **上下文感知重写**：使用对话历史解析代词
- **渐进式搜索**：类别 → 条目 → 资源
- **充分性检查**：当检索到足够信息时停止

#### 使用示例

```python
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "他们的偏好是什么？"}},
        {"role": "user", "content": {"text": "告诉我工作习惯"}}
    ],
    where={"user_id": "123"}  # 可选：范围过滤器
)

# 返回：
{
    "categories": [...],     # 相关类别（RAG 包含分数）
    "items": [...],          # 相关记忆条目
    "resources": [...],      # 相关原始资源
    "next_step_query": "..." # 重写的后续查询（如适用）
}
```

**范围过滤**：使用 `where` 按用户模型字段过滤：
- `where={"user_id": "123"}` - 精确匹配
- `where={"agent_id__in": ["1", "2"]}` - 匹配列表中的任意项
- 省略 `where` 以检索所有范围

> 📚 **完整 API 文档**，请参阅 [SERVICE_API.md](docs/SERVICE_API.md) - 包含所有方法、CRUD 操作、管道配置和配置类型。

---

## 💡 使用案例

### 示例 1：对话记忆

从多轮对话中提取和组织记忆：

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**功能：**
- 处理多个对话 JSON 文件
- 提取记忆条目（偏好、习惯、观点、关系）
- 生成类别 Markdown 文件（`preferences.md`、`work_life.md` 等）

**适用场景：** 个人 AI 助手、客户支持机器人、社交聊天机器人

---

### 示例 2：从日志中提取技能

从智能体执行日志中提取技能和经验教训：

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**功能：**
- 顺序处理智能体日志
- 提取操作、结果和经验教训
- 展示**增量学习** - 记忆随每个文件演化
- 生成演化的技能指南（`log_1.md` → `log_2.md` → `skill.md`）

**适用场景：** DevOps 团队、智能体自我改进、知识管理

---

### 示例 3：多模态记忆

将多种内容类型处理为统一记忆：

```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**功能：**
- 同时处理文档和图像
- 从不同内容类型提取记忆
- 统一到跨模态类别（`technical_documentation`、`visual_diagrams` 等）

**适用场景：** 文档系统、学习平台、研究工具

---

## 📊 性能表现

MemU 在 Locomo 基准测试中，在所有推理任务上实现了 **92.09% 的平均准确率**。

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

查看详细实验数据：[memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 生态系统

| 仓库 | 描述 | 使用场景 |
|------|------|----------|
| **[memU](https://github.com/NevaMind-AI/memU)** | 核心算法引擎 | 将 AI 记忆嵌入到你的产品中 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | 带 CRUD、用户系统、RBAC 的后端服务 | 自托管记忆后端 |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | 可视化仪表板 | 即用型记忆控制台 |

**快速链接：**
- 🚀 [试用 MemU 云服务](https://app.memu.so/quick-start)
- 📚 [API 文档](https://memu.pro/docs)
- 💬 [Discord 社区](https://discord.gg/memu)

---

## 🤝 合作伙伴

<div align="center">

<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://openagents.org"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Milvus" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="Jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="Buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="Bytebase" height="40" style="margin: 10px;"></a>
<a href="https://github.com/LazyAGI/LazyLLM"><img src="assets/partners/LazyLLM.png" alt="LazyLLM" height="40" style="margin: 10px;"></a>

</div>

---

## 📄 许可证

[Apache License 2.0](LICENSE.txt)

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

---

## 🎯 项目学习指南

### 学习路径建议

1. **入门阶段**
   - 阅读本文档，了解项目整体架构
   - 运行快速开始示例，体验基本功能
   - 查看 `examples/` 目录中的使用案例

2. **深入理解**
   - 研究 `src/memu/` 目录下的核心代码
   - 理解三层架构的实现细节
   - 学习双检索策略的工作原理

3. **贡献准备**
   - 查看 `CONTRIBUTING.md`（如有）
   - 了解项目代码规范和测试要求
   - 参与社区讨论，了解项目需求

### 技术栈要点
- **Python 3.13+**：项目要求 Python 3.13 或更高版本
- **异步编程**：大量使用 async/await 语法
- **SQLModel**：用于数据库操作的 ORM
- **Pydantic**：数据验证和设置管理
- **OpenAI API**：默认的 LLM 和嵌入提供者

### 开发环境搭建
```bash
# 克隆项目
git clone https://github.com/NevaMind-AI/memU.git
cd memU

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .[dev]
```

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

有关详细的贡献指南、代码标准和开发实践，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

**快速提示：**
- 为每个功能或错误修复创建新分支
- 编写清晰的提交信息
- 为新功能添加测试
- 根据需要更新文档
- 推送前运行 `make check`

### 贡献方向

#### 🐛 报告问题
- 在 GitHub Issues 中报告 bug
- 提出功能建议
- 改进文档

#### 💻 代码贡献
- 修复已知问题
- 实现新功能
- 优化现有代码
- 添加测试用例

#### 📚 文档贡献
- 改进现有文档
- 添加使用示例
- 翻译文档（如本文档）
- 编写教程

#### 🧪 测试贡献
- 添加单元测试
- 编写集成测试
- 进行性能测试
- 报告测试覆盖率

### 贡献流程
1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feat/your-feature`)
3. 提交更改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feat/your-feature`)
5. 创建 Pull Request

---

## 📈 项目发展路线

### 近期目标
- 提高多模态处理能力
- 优化检索性能和准确性
- 扩展支持的 LLM 和嵌入提供者
- 完善文档和示例

### 长期愿景
- 构建完整的 AI 记忆生态系统
- 支持更多应用场景和行业
- 实现更智能的自演化能力
- 推动 AI 记忆技术的标准化

---

## ❓ 常见问题

### Q: MemU 与其他记忆系统有何不同？
A: MemU 的主要特点是分层文件系统架构和双检索策略，结合了 RAG 的高效性和 LLM 的深度理解能力。

### Q: 是否需要数据库支持？
A: 不需要。MemU 支持内存存储模式，无需数据库即可运行。但对于生产环境，建议使用 PostgreSQL 等数据库。

### Q: 支持哪些 LLM 提供者？
A: 除了默认的 OpenAI，还支持自定义 LLM 和嵌入提供者，如阿里云、VoyageAI 等。

### Q: 项目对 Python 版本有何要求？
A: 需要 Python 3.13 或更高版本。

### Q: 如何获取技术支持？
A: 可以通过 GitHub Issues、Discord 社区或邮件联系项目团队。

---

<div align="center">

**感谢你对 MemU 项目的关注和支持！**

让我们一起构建更好的 AI 记忆系统！🚀

</div>
