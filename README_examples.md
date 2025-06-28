# PersonaLab + OpenAI Integration Examples

这些示例展示了如何使用 `enhance_system_prompt_with_memory` 函数将 PersonaLab 内存系统与 OpenAI Chat API 集成。

## 📁 文件说明

### 1. `simple_openai_example.py` - 简洁示例
最简单的集成示例，使用现代 OpenAI API (v1.x)：

```python
from personalab.utils import enhance_system_prompt_with_memory
from personalab.memory import MemoryClient

# 创建内存客户端
memory_client = MemoryClient("example.db")
memory = memory_client.get_or_create_memory("user_001")

# 增强系统提示符
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt="You are a helpful assistant.",
    memory=memory,
    include_profile=True,
    include_events=True,
    include_insights=True
)
```

### 2. `example_openai_chat.py` - 完整示例
更详细的示例，包含：
- 完整的对话流程
- 内存数据的创建和管理
- 多轮对话演示
- 两种使用方式对比

## 🚀 快速开始

### 1. 环境设置

```bash
# 安装依赖
pip install openai

# 设置 OpenAI API Key
export OPENAI_API_KEY="your-api-key-here"
```

### 2. 基本用法

```python
#!/usr/bin/env python3
import os
from openai import OpenAI
from personalab.utils import enhance_system_prompt_with_memory
from personalab.memory import MemoryClient

# 初始化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
memory_client = MemoryClient("my_memory.db")

# 创建内存数据
memory = memory_client.get_or_create_memory("user_123")
memory.update_profile("用户是一个Python开发者，喜欢简洁的代码")
memory.update_events(["讨论了FastAPI的使用", "询问了异步编程"])

# 增强提示符
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt="你是一个Python专家助手",
    memory=memory
)

# 使用增强后的提示符与OpenAI聊天
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": enhanced_prompt},
        {"role": "user", "content": "如何优化我的Python代码？"}
    ]
)

print(response.choices[0].message.content)
```

## 🔧 核心功能

### `enhance_system_prompt_with_memory` 参数说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `base_system_prompt` | str | 基础系统提示符 | 必需 |
| `memory` | Memory \| str | Memory对象或agent_id | 必需 |
| `memory_client` | MemoryClient | 内存客户端（memory为str时必需） | None |
| `include_profile` | bool | 是否包含用户画像 | True |
| `include_events` | bool | 是否包含历史事件 | True |
| `include_insights` | bool | 是否包含行为洞察 | True |
| `max_events` | int | 最大事件数量 | 10 |
| `max_insights` | int | 最大洞察数量 | 5 |
| `memory_section_title` | str | 内存部分标题 | "## Memory Context" |

### 两种使用方式

#### 方式1：直接传递 Memory 对象
```python
memory = memory_client.get_or_create_memory("user_001")
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt="你是助手",
    memory=memory  # 直接传递Memory对象
)
```

#### 方式2：传递 agent_id 字符串
```python
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt="你是助手",
    memory="user_001",  # 传递agent_id
    memory_client=memory_client  # 必须提供客户端
)
```

## 📊 内存数据结构

PersonaLab 内存系统包含三个主要组件：

### 1. Profile Memory (画像记忆)
存储用户的基本信息、偏好、特征等：

```python
memory.update_profile("""
用户是一个28岁的软件工程师，住在北京。
喜欢Python和JavaScript，对AI/ML很感兴趣。
工作风格追求效率，喜欢干净的代码。
""")
```

### 2. Event Memory (事件记忆)  
存储历史对话和重要事件：

```python
memory.update_events([
    "用户询问了如何优化数据库查询",
    "讨论了微服务架构的最佳实践",
    "用户提到正在开发一个新的API项目"
])
```

### 3. Theory of Mind Memory (心理模型记忆)
存储对用户行为模式和心理特征的洞察：

```python
memory.update_tom([
    "用户倾向于要求实用的、可执行的建议",
    "对新技术保持开放态度，但重视稳定性",
    "喜欢通过实例学习，而非理论说明"
])
```

## 💡 最佳实践

### 1. 内存数据管理
- 定期更新用户画像信息
- 限制事件数量避免prompt过长
- 根据对话内容动态调整洞察

### 2. 提示符优化
- 根据场景选择包含的内存组件
- 调整 `max_events` 和 `max_insights` 控制长度
- 使用有意义的 `memory_section_title`

### 3. 性能考虑
- 使用数据库持久化内存数据
- 合理设置内存大小限制
- 考虑使用缓存优化频繁访问

## 🔄 集成现有应用

如果你已有 OpenAI 聊天应用，集成 PersonaLab 只需几步：

```python
# 原有代码
messages = [
    {"role": "system", "content": "你是助手"},
    {"role": "user", "content": user_input}
]

# 集成PersonaLab后
memory_client = MemoryClient("app_memory.db")
enhanced_system_prompt = enhance_system_prompt_with_memory(
    base_system_prompt="你是助手",
    memory=user_id,
    memory_client=memory_client
)

messages = [
    {"role": "system", "content": enhanced_system_prompt},  # 使用增强后的提示符
    {"role": "user", "content": user_input}
]
```

## 🏃 运行示例

```bash
# 运行简单示例
python simple_openai_example.py

# 运行完整示例
python example_openai_chat.py
```

如果没有设置 `OPENAI_API_KEY`，示例会运行演示模式，展示增强后的提示符而不调用 OpenAI API。

## 📚 更多资源

- [PersonaLab 文档](../README.md)
- [Memory 架构说明](../STRUCTURE.md)
- [OpenAI API 文档](https://platform.openai.com/docs) 