# PersonaLab 示例集合

本目录包含了PersonaLab的完整使用示例，从基础功能到高级应用场景。这些示例经过重新设计，结构清晰，逐步递进，帮助您快速掌握PersonaLab的各种功能。

## 📚 示例概览

| 示例文件 | 难度 | 主要功能 | 描述 |
|---------|------|----------|------|
| `01_basic_memory.py` | 🌟 基础 | Memory模块 | AI代理内存管理基础操作 |
| `02_conversation_recording.py` | 🌟 基础 | Memo模块 | 对话记录和存储管理 |
| `03_semantic_search.py` | 🌟🌟 中级 | 语义搜索 | 向量embedding和语义搜索 |
| `04_user_management.py` | 🌟🌟 中级 | 用户管理 | 多用户数据管理和分析 |
| `05_integration.py` | 🌟🌟🌟 高级 | 模块集成 | Memory+Memo完整集成应用 |
| `06_advanced_usage.py` | 🌟🌟🌟 高级 | 企业应用 | 批量处理和多代理协作 |
| `07_openai_chatbot_integration.py` | 🌟🌟🌟 高级 | OpenAI集成 | 真实生产级AI chatbot实现 |

## 🚀 快速开始

### 环境准备

1. **确保依赖安装**
```bash
pip install -r requirements.txt
```

2. **配置OpenAI API（可选，用于高质量embedding）**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 运行示例

所有示例都可以独立运行：

```bash
# 基础示例
python examples/01_basic_memory.py
python examples/02_conversation_recording.py

# 中级示例
python examples/03_semantic_search.py
python examples/04_user_management.py

# 高级示例
python examples/05_integration.py
python examples/06_advanced_usage.py

# OpenAI集成示例（需要API密钥）
export OPENAI_API_KEY="your-api-key"
python examples/07_openai_chatbot_integration.py
python examples/07_openai_chatbot_integration.py interactive  # 交互模式
```

## 📖 详细说明

### 01. 基础内存管理 (`01_basic_memory.py`)

**目标**: 学习PersonaLab Memory模块的基础操作

**核心功能**:
- 创建AI代理内存
- 更新Profile、Events、Theory of Mind
- 内存状态的保存和加载
- 基础的内存操作

**适用场景**: 
- AI助手的个性化记忆
- 用户偏好学习
- 对话上下文保持

**学习重点**:
```python
# 创建内存管理器
memory_manager = MemoryManager(db_path="demo.db")

# 获取代理内存
memory = memory_manager.get_or_create_memory("agent_id")

# 更新内存组件
memory.update_profile("我是学习助手...")
memory.update_events(["用户询问了Python"])
memory.update_tom(["用户是编程初学者"])
```

### 02. 对话记录管理 (`02_conversation_recording.py`)

**目标**: 掌握PersonaLab Memo模块的对话记录功能

**核心功能**:
- 记录对话到数据库
- 管理必须字段（user_id, agent_id, created_at）
- 对话历史查询和过滤
- 会话管理

**适用场景**:
- 客服系统对话记录
- 教学对话历史
- 多轮对话管理

**学习重点**:
```python
# 创建对话管理器
conversation_manager = ConversationManager(
    db_path="conversations.db",
    enable_embeddings=False
)

# 记录对话（必须字段）
conversation = conversation_manager.record_conversation(
    agent_id="customer_service",    # 必须
    user_id="customer_001",         # 必须
    messages=[...],                 # 必须
    session_id="session_001"        # 可选
)
```

### 03. 语义搜索 (`03_semantic_search.py`)

**目标**: 理解向量embedding和语义搜索的工作原理

**核心功能**:
- 启用向量embedding
- 自动生成对话向量
- 语义相似度搜索
- 搜索阈值和相似度分析

**适用场景**:
- 智能客服知识库
- 教育内容推荐
- 相似问题检索

**学习重点**:
```python
# 启用embedding
conversation_manager = ConversationManager(
    db_path="search_demo.db",
    enable_embeddings=True,          # 关键设置
    embedding_provider="auto"
)

# 语义搜索
results = conversation_manager.search_similar_conversations(
    agent_id="assistant",
    query="Python学习资源",
    limit=5,
    similarity_threshold=0.6         # 相似度阈值
)
```

### 04. 用户管理 (`04_user_management.py`)

**目标**: 学习多用户环境下的数据管理和分析

**核心功能**:
- 多用户对话数据管理
- 按用户过滤对话和搜索
- 用户行为分析
- 跨用户数据统计

**适用场景**:
- 多租户AI平台
- 用户画像分析
- 个性化服务

**学习重点**:
```python
# 按用户过滤对话
user_conversations = conversation_manager.get_conversation_history(
    agent_id="assistant",
    user_id="user_001",              # 用户过滤
    limit=10
)

# 用户特定的语义搜索
user_results = conversation_manager.search_similar_conversations(
    agent_id="assistant",
    query="学习进度",
    user_id="user_001"               # 可选用户过滤
)
```

### 05. 模块集成 (`05_integration.py`)

**目标**: 掌握Memory和Memo模块的完整集成应用

**核心功能**:
- Memory + Memo协同工作
- 从对话中自动提取记忆
- 基于记忆状态生成响应
- 完整的AI学习循环

**适用场景**:
- 智能教学系统
- 个人AI助手
- 自适应对话机器人

**学习重点**:
```python
# 双模块初始化
memory_manager = MemoryManager(db_path="memory.db")
conversation_manager = ConversationManager(db_path="conversations.db")

# 从对话更新记忆
def update_memory_from_conversation(memory, messages):
    # 提取事件
    events = extract_events_from_conversation(messages)
    memory.update_events(events)
    
    # 提取洞察
    insights = extract_insights_from_conversation(messages, memory.get_tom_content())
    memory.update_tom(insights)
```

### 06. 高级应用 (`06_advanced_usage.py`)

**目标**: 掌握企业级应用的高级功能和最佳实践

**核心功能**:
- 批量处理大量对话数据
- 多代理协作和知识共享
- 性能优化和错误处理
- 详细分析报告生成

**适用场景**:
- 企业级AI平台
- 大规模数据处理
- 多代理系统

**学习重点**:
```python
# 高级管理器
class AdvancedPersonaLabManager:
    def batch_process_conversations(self, conversations_data):
        # 批量处理逻辑
        pass
    
    def knowledge_transfer(self, source_agent, target_agent, topics):
        # 代理间知识转移
        pass
    
    def generate_agent_report(self, agent_id):
        # 详细分析报告
        pass
```

### 07. OpenAI集成 (`07_openai_chatbot_integration.py`)

**目标**: 展示PersonaLab memory管理与OpenAI API的集成

**核心功能**:
- 直接使用OpenAI API进行对话
- utils.py封装的memory管理功能
- 自动学习用户偏好和特征
- 历史对话上下文检索

**适用场景**:
- 智能聊天机器人开发
- AI助手记忆增强
- 个性化对话系统
- PersonaLab与外部AI服务集成

**学习重点**:
```python
# 创建PersonaLab组件
memory_manager = create_memory_manager("memory.db")
conversation_manager = create_conversation_manager("conversations.db")

# 构建包含记忆的系统提示
system_prompt = build_system_prompt(memory_manager, conversation_manager, agent_id, user_message)

# 直接调用OpenAI API
response = openai_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "system", "content": system_prompt}, ...]
)

# 学习并更新记忆
learn_from_conversation(memory_manager, conversation_manager, agent_id, user_id, messages)
```

**运行方式**:
- **演示模式**: `python 07_openai_chatbot_integration.py`
- **交互模式**: `python 07_openai_chatbot_integration.py interactive`
- **记忆查看**: 在交互模式输入 `memory`

**环境要求**:
```bash
export OPENAI_API_KEY="your-openai-api-key"
pip install openai>=1.0.0
```

## 🛠️ 实用技巧

### 数据库文件管理

示例会在运行目录创建数据库文件：
```
basic_memory_demo.db
conversation_demo.db
semantic_search_demo.db
user_management_demo.db
integration_memory.db
integration_conversations.db
advanced_memory.db
advanced_conversations.db
chatbot_memory.db
chatbot_conversations.db
```

可以安全删除这些文件重新运行示例。

### OpenAI API配置

如果您有OpenAI API密钥，设置环境变量可以获得更好的embedding质量：
```bash
export OPENAI_API_KEY="sk-..."
```

否则系统会自动使用免费的SentenceTransformers embedding。

### 性能优化建议

1. **对于大量数据**: 使用`06_advanced_usage.py`中的批量处理方法
2. **对于高频搜索**: 适当调整`similarity_threshold`平衡精度和召回
3. **对于内存使用**: 定期清理不需要的对话历史

## 📦 共享工具函数 (`../utils.py`)

为避免代码重复和提高复用性，常用的工具函数被抽取到项目根目录的 `utils.py` 中：

### 对话处理函数

1. **simulate_ai_response()** - 模拟AI响应（用于演示）
2. **extract_events_from_conversation()** - 从对话中提取重要事件
3. **extract_insights_from_conversation()** - 提取用户洞察和特征
4. **analyze_user_interest_keywords()** - 分析用户兴趣关键词
5. **generate_learning_path_suggestions()** - 生成学习路径建议
6. **format_conversation_summary()** - 格式化对话摘要
7. **validate_conversation_data()** - 验证对话数据完整性

### Memory管理函数

8. **create_memory_manager()** - 创建Memory管理器
9. **create_conversation_manager()** - 创建对话管理器
10. **setup_agent_memory()** - 设置agent的初始记忆
11. **get_memory_context()** - 获取记忆上下文用于AI提示
12. **get_conversation_context()** - 获取相关的历史对话上下文
13. **build_system_prompt()** - 构建包含记忆的系统提示
14. **learn_from_conversation()** - 从对话中学习并更新记忆
15. **get_memory_summary()** - 获取记忆摘要
16. **cleanup_memory_resources()** - 清理记忆管理相关资源

**使用示例**:
```python
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils import create_memory_manager, build_system_prompt, learn_from_conversation

# 创建组件
memory_manager = create_memory_manager("my_memory.db")

# 构建系统提示
prompt = build_system_prompt(memory_manager, conversation_manager, agent_id, user_message)

# 学习并更新记忆
learn_from_conversation(memory_manager, conversation_manager, agent_id, user_id, messages)
```

这种设计让您可以：
- **复用代码**: 避免在多个示例中重复相同的函数
- **模块化开发**: 只导入需要的功能
- **易于维护**: 统一的工具函数便于更新和修复
- **灵活集成**: 直接在您的项目中使用这些工具函数

## 🔧 故障排除

### 常见问题

1. **ImportError**: 确保安装了所有依赖
```bash
pip install -r requirements.txt
```

2. **数据库锁定**: 确保没有其他进程在使用数据库文件

3. **Embedding错误**: 检查网络连接或OpenAI API密钥

4. **内存不足**: 对于大型数据集，考虑分批处理

### 获取帮助

- 查看项目根目录的`README.md`
- 检查`docs/`目录中的详细文档
- 运行示例时注意控制台输出的详细信息

## 📈 进阶学习路径

1. **初学者**: 01 → 02 → 03
2. **开发者**: 01 → 02 → 03 → 04 → 05
3. **企业用户**: 全部示例 + 自定义扩展

## 🎯 下一步

运行完这些示例后，您可以：

1. 基于示例代码构建自己的应用
2. 探索项目文档了解更多高级功能
3. 参考源代码进行自定义开发
4. 加入社区分享您的使用经验

祝您使用愉快！🚀 