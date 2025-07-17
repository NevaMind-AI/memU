# DeepSeek Integration Guide

本文档说明如何在MemU项目中集成和使用DeepSeek模型。

## 新增功能

### 1. DeepSeek客户端

创建了一个新的`DeepSeekClient`类，位于`memu/llm/deepseek_client.py`，支持：

- 使用Azure AI Inference库连接DeepSeek模型
- 支持聊天补全和函数调用
- 与现有LLM客户端架构完全兼容

### 2. 自动客户端选择

创建了`llm_factory.py`工厂函数，可以根据模型名称自动选择合适的客户端：

- DeepSeek模型（包含"deepseek"的模型名称）→ 使用DeepSeekClient
- 其他模型 → 使用AzureOpenAIClient

### 3. 代理更新

更新了以下代理以支持DeepSeek：

- `MemAgent` - 内存管理代理
- `ResponseAgent` - 问答代理  
- `EvaluateAgent` - 评估代理

## 环境配置

### 所需环境变量

```bash
# DeepSeek配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_ENDPOINT=https://ai-sairin12027701ai851284620530.services.ai.azure.com/models

# Azure OpenAI配置（用于其他模型）
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
```

### 所需依赖

```bash
pip install azure-ai-inference
pip install azure-core
```

## 使用方法

### 1. 直接使用DeepSeekClient

```python
from memu.llm import DeepSeekClient

# 创建客户端
client = DeepSeekClient(
    api_key="your_api_key",
    endpoint="https://ai-sairin12027701ai851284620530.services.ai.azure.com/models",
    model_name="DeepSeek-V3-0324"
)

# 简单聊天
response = client.simple_chat("你好，请介绍一下你自己")
print(response)

# 详细聊天补全
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "你是一个有用的助手。"},
        {"role": "user", "content": "解释一下量子计算的基本原理"}
    ],
    temperature=0.7,
    max_tokens=2000
)

if response.success:
    print(response.content)
    print(f"模型: {response.model}")
    print(f"使用情况: {response.usage}")
```

### 2. 在代理中使用

```python
from scripts.evals.locomo.mem_agent import MemAgent

# 使用DeepSeek模型创建内存代理
agent = MemAgent(
    chat_deployment="DeepSeek-V3-0324",  # 自动选择DeepSeek客户端
    memory_dir="memory"
)

# 更新角色内存
result = agent.update_character_memory(
    session_data=conversation_data,
    session_date="2024-01-01",
    characters=["Alice", "Bob"]
)
```

### 3. 在测试中使用

```python
# 在locomo_test.py中使用DeepSeek
python locomo_test.py --chat-deployment DeepSeek-V3-0324
```

## 功能支持

### ✅ 已支持的功能

- [x] 基本聊天补全
- [x] 函数调用（Tool Calling）
- [x] 流式响应参数（temperature, max_tokens, top_p等）
- [x] 系统消息、用户消息、助手消息
- [x] 工具消息支持
- [x] 错误处理和重试机制
- [x] 与现有代理的完全兼容

### 🔧 配置选项

```python
DeepSeekClient(
    api_key="your_api_key",           # API密钥
    endpoint="your_endpoint",         # API端点
    model_name="DeepSeek-V3-0324",   # 模型名称
    api_version="2024-05-01-preview", # API版本
)
```

### 🎯 使用场景

1. **内存管理**: 使用DeepSeek进行对话分析和内存提取
2. **问答系统**: 使用DeepSeek回答基于内存的问题
3. **评估系统**: 使用DeepSeek评估答案质量和相关性
4. **多模型对比**: 在同一系统中比较不同模型的表现

## 示例文件

- `examples/deepseek_client_example.py` - DeepSeek客户端基本使用示例
- `scripts/evals/locomo/llm_factory.py` - 客户端工厂函数
- `memu/llm/deepseek_client.py` - DeepSeek客户端实现

## 注意事项

1. **API兼容性**: DeepSeek使用Azure AI Inference，与OpenAI API略有不同
2. **消息格式**: 自动转换为Azure AI Inference所需的消息格式
3. **错误处理**: 包含完整的错误处理和日志记录
4. **类型安全**: 包含类型提示和运行时验证

## 故障排除

### 常见问题

1. **导入错误**: 确保安装了`azure-ai-inference`依赖
2. **认证失败**: 检查API密钥和端点URL是否正确
3. **模型不可用**: 确认模型名称和API版本是否正确

### 调试信息

启用详细日志记录：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

这将显示详细的API调用和响应信息，有助于诊断问题。 