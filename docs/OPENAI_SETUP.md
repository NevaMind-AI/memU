# OpenAI Embedding 配置指南

PersonaLab memo模块支持使用OpenAI的高质量embedding来进行语义搜索。

## 前置要求

### 1. 安装OpenAI库
```bash
pip install openai
```

### 2. 获取OpenAI API Key
1. 访问 [OpenAI API Keys页面](https://platform.openai.com/api-keys)
2. 登录你的OpenAI账户
3. 点击 "Create new secret key" 创建新的API key
4. 复制生成的API key（以sk-开头）

### 3. 设置环境变量

#### macOS/Linux:
```bash
# 临时设置（当前会话有效）
export OPENAI_API_KEY="your_api_key_here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows:
```cmd
# Command Prompt
set OPENAI_API_KEY=your_api_key_here

# PowerShell
$env:OPENAI_API_KEY="your_api_key_here"

# 永久设置（系统环境变量）
# 控制面板 > 系统 > 高级系统设置 > 环境变量
```

#### 或者创建 .env 文件:
在项目根目录创建 `.env` 文件：
```
OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 基本使用
```python
from personalab.memo import ConversationManager

# 使用OpenAI embedding
manager = ConversationManager(
    db_path="conversations.db",
    enable_embeddings=True,
    embedding_provider="openai"  # 使用OpenAI embeddings
)

# 记录对话
conversation = manager.record_conversation(
    agent_id="agent_1",
    messages=[
        {"role": "user", "content": "你好，我对机器学习很感兴趣"},
        {"role": "assistant", "content": "很好！机器学习是一个非常有趣的领域。"}
    ],
    user_id="user_123"
)

# 语义搜索
results = manager.search_similar_conversations(
    agent_id="agent_1",
    query="人工智能 深度学习",
    limit=5
)
```

### 高级配置
```python
# 指定特定的OpenAI模型
manager = ConversationManager(
    db_path="conversations.db",
    enable_embeddings=True,
    embedding_provider="openai",
    model="text-embedding-ada-002"  # 默认模型
)

# 带错误处理的自动回退
try:
    manager = ConversationManager(
        embedding_provider="openai"
    )
    print("使用OpenAI embeddings")
except Exception as e:
    print(f"OpenAI不可用，尝试其他provider: {e}")
    try:
        manager = ConversationManager(
            embedding_provider="sentence-transformers"
        )
        print("使用SentenceTransformer embeddings")
    except Exception as e2:
        print(f"无可用的embedding provider: {e2}")
        raise RuntimeError("请安装 openai 或 sentence-transformers 库")
```

## 运行示例

### 测试OpenAI embedding
```bash
# 设置API key后运行
export OPENAI_API_KEY="your_key_here"
python examples/memo_openai_embedding_example.py
```

### 运行自动选择示例
```bash
# 自动选择最佳可用的embedding provider
python examples/memo_simple_example.py
```

## Embedding Provider 对比

| 特性 | SentenceTransformers | OpenAI Embedding |
|------|---------------------|-------------------|
| 维度 | 384-768维 | 1536维 |
| 语义理解 | 优秀 | 顶级 |
| 跨语言支持 | 良好 | 优秀 |
| 上下文理解 | 良好 | 复杂 |
| API依赖 | 无 | 需要 |
| 成本 | 免费 | 按使用付费 |
| 部署方式 | 本地运行 | 云端API |

## 常见问题

### Q: 如何检查API key是否正确设置？
```python
import os
print(f"API Key: {os.getenv('OPENAI_API_KEY', 'Not set')}")
```

### Q: API调用失败怎么办？
系统会自动尝试其他可用的embedding provider（如SentenceTransformers），确保功能正常运行。如果没有可用的provider，会抛出错误提示安装相应库。

### Q: 成本考虑？
- text-embedding-ada-002: $0.0001 / 1K tokens
- 一般对话每次embedding约消耗$0.0001-0.001

### Q: 如何监控embedding使用情况？
```python
stats = manager.get_conversation_stats(agent_id)
print(f"Embedding model: {stats['embedding_model']}")
print(f"Total conversations: {stats['total_conversations']}")
```

## 故障排除

1. **ImportError: No module named 'openai'**
   ```bash
   pip install openai
   ```

2. **API key错误**
   - 检查key是否正确复制
   - 确认key没有多余空格
   - 验证key是否有效且有足够额度

3. **网络连接问题**
   - 检查网络连接
   - 考虑使用代理设置

4. **权限问题**
   - 确认API key有embedding权限
   - 检查组织设置（如果适用） 