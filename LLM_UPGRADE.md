# 🤖 PersonaLab LLM驱动升级

PersonaLab现在完全使用LLM来进行Memory分析和更新，统一架构，告别规则性逻辑！

## 🚀 主要变化

### ✅ LLM驱动功能
- **统一Pipeline**: 完全基于LLM的Memory更新流程
- **智能分析**: LLM自动分析对话并提取用户画像信息
- **自然更新**: LLM生成连贯自然的用户画像描述
- **深度ToM**: LLM进行Theory of Mind心理分析

### 🔄 架构简化
- **LLM Client**: 统一的LLM接口，支持OpenAI、Mock等
- **单一Pipeline**: 移除传统规则驱动，只保留LLM驱动
- **向后兼容**: 保持所有原有API接口不变

## 💡 使用方式

### 最简单的使用（默认LLM驱动）
```python
from personalab.memory import MemoryManager

# 创建LLM驱动的Memory管理器
manager = MemoryManager()  # 默认使用LLM

# 你的conversation
conversation = [
    {'role': 'user', 'content': '我是张三，程序员'},
    {'role': 'assistant', 'content': '你好张三！'}
]

# 处理conversation
memory, result = manager.update_memory_with_conversation("user_001", conversation)
print(memory.to_prompt())
```

### 自定义LLM配置
```python
from personalab.llm import create_llm_client
from personalab.memory import MemoryManager

# 使用OpenAI
llm_client = create_llm_client("openai", api_key="your-key")
manager = MemoryManager(
    llm_client=llm_client,
    temperature=0.3,
    max_tokens=2000
)

# 基础功能（无需API）
manager = MemoryManager()  # 自动使用fallback功能
```

### 创建Memory管理器
```python
# 现在只有一种方式，都是LLM驱动
manager = MemoryManager()  # 默认LLM驱动
```

## 🎯 LLM驱动优势

### 🧠 智能分析
- 理解对话语义和上下文
- 自动识别重要信息
- 智能去重和整合

### 🌟 自然表达
- 生成连贯的用户画像
- 避免简单拼接的生硬感
- 保持信息的准确性

### 🔮 深度洞察
- Theory of Mind心理分析
- 意图、情绪、行为模式识别
- 认知状态评估

## 🔧 支持的LLM

### OpenAI
```python
from personalab.llm import create_llm_client

client = create_llm_client("openai", 
    api_key="your-openai-key",
    base_url="https://api.openai.com/v1"  # 可选
)
```

### 基础功能（无需API）
```python
# 直接使用MemoryManager，自动fallback到基础功能
manager = MemoryManager()  # 无需LLM配置
```

### 扩展其他LLM
```python
from personalab.llm import BaseLLMClient

class CustomLLMClient(BaseLLMClient):
    def chat_completion(self, messages, **kwargs):
        # 实现你的LLM调用逻辑
        pass
```

## 📊 Pipeline流程

1. **分析阶段**: LLM分析对话，提取画像更新和事件
2. **更新阶段**: LLM整合信息，生成自然的用户画像
3. **ToM阶段**: LLM进行深度心理分析

## 🚀 易于扩展
- 支持多种LLM后端
- 可配置的prompt模板
- 灵活的参数调节

## 📝 示例文件

- `llm_conversation_example.py` - 完整的LLM使用示例
- `conversation_example.py` - 更新为默认使用LLM
- `simple_conversation_template.py` - 简洁的LLM使用模板

## 🔄 迁移指南

### 现有代码无需修改
```python
# 这些代码无需任何修改，自动使用LLM
manager = MemoryManager()
memory, result = manager.update_memory_with_conversation(agent_id, conversation)
```

### 简洁的API设计
```python
# 只有一种方式，统一LLM驱动
manager = MemoryManager()  # 简单明了
```

## 🎯 最佳实践

1. **生产环境**: 使用OpenAI或其他真实LLM，获得最佳智能分析
2. **开发测试**: 使用基础功能，无需API密钥即可测试
3. **参数调节**: temperature=0.3 保证稳定性
4. **错误处理**: LLM失败时自动降级到基础方案

---

🎉 **PersonaLab现在采用统一的LLM驱动架构，让Memory更新变得更加智能、自然和简洁！** 