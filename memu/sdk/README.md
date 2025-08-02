# MemU Python SDK

MemU Python SDK 为 MemU API 服务提供了简单易用的 HTTP 客户端。

## 功能特性

- 🚀 **简单易用** - 简洁的 API 接口，易于集成
- 🔄 **自动重试** - 内置请求重试机制，提高可靠性
- 🛡️ **错误处理** - 完善的异常处理和错误分类
- 📝 **类型安全** - 使用 Pydantic 模型进行数据验证
- 🌐 **异步支持** - 支持上下文管理器自动资源清理
- 📊 **详细日志** - 内置日志记录，便于调试

## 安装

MemU SDK 是 MemU 包的一部分：

```bash
pip install memu-py
```

## 快速开始

### 基本用法

```python
from memu.sdk import MemuClient

# 初始化客户端
client = MemuClient(
    base_url="https://api.memu.ai",
    api_key="your-api-key-here"
)

# 记忆化对话
response = client.memorize_conversation(
    conversation_text="User: I love hiking. Assistant: That's great! What's your favorite trail?",
    user_id="user_123",
    user_name="Alice",
    agent_id="agent_456",
    agent_name="AI Assistant", 
    project_id="project_789"
)

print(f"Task ID: {response.task_id}")
print(f"Status: {response.status}")

# 关闭客户端
client.close()
```

### 使用上下文管理器

```python
from memu.sdk import MemuClient

with MemuClient(
    base_url="https://api.memu.ai",
    api_key="your-api-key-here"
) as client:
    response = client.memorize_conversation(
        conversation_text="User: What's the weather? Assistant: It's sunny today!",
        user_id="user_001",
        user_name="Bob",
        agent_id="weather_bot",
        agent_name="Weather Bot",
        project_id="weather_app"
    )
    print(f"Task created: {response.task_id}")
```

### 使用环境变量

```python
import os

# 设置环境变量
os.environ["MEMU_API_BASE_URL"] = "https://api.memu.ai"
os.environ["MEMU_API_KEY"] = "your-api-key-here"

# 客户端会自动读取环境变量
client = MemuClient()
```

## API 参考

### MemuClient

主要的 HTTP 客户端类。

#### 构造函数

```python
MemuClient(
    base_url: str = None,           # API 服务器基础 URL
    api_key: str = None,            # API 密钥
    timeout: float = 30.0,          # 请求超时时间（秒）
    max_retries: int = 3,           # 最大重试次数
    **kwargs                        # 其他 httpx 客户端参数
)
```

#### 方法

##### memorize_conversation

启动 Celery 任务来记忆化对话文本。

```python
memorize_conversation(
    conversation_text: str,     # 要记忆的对话文本
    user_id: str,              # 用户标识符
    user_name: str,            # 用户显示名称
    agent_id: str,             # 代理标识符
    agent_name: str,           # 代理显示名称
    project_id: str,           # 项目标识符
    api_key_id: str = None     # API 密钥标识符（可选）
) -> MemorizeResponse
```

**返回值**: `MemorizeResponse` 对象，包含任务 ID 和状态信息。

##### get_task_status

获取记忆化任务的状态。

```python
get_task_status(task_id: str) -> Dict[str, Any]
```

**参数**:
- `task_id`: 从 `memorize_conversation` 返回的任务标识符

**返回值**: 包含任务状态信息的字典。

### 数据模型

#### MemorizeRequest

记忆化对话的请求模型。

```python
class MemorizeRequest:
    conversation_text: str    # 对话文本
    user_id: str             # 用户标识符
    user_name: str           # 用户显示名称
    agent_id: str            # 代理标识符
    agent_name: str          # 代理显示名称
    api_key_id: str          # API 密钥标识符
    project_id: str          # 项目标识符
```

#### MemorizeResponse

记忆化对话的响应模型。

```python
class MemorizeResponse:
    task_id: str             # Celery 任务 ID
    status: str              # 任务状态
    message: str             # 响应消息
```

### 异常处理

SDK 提供了以下异常类：

#### MemuSDKException
所有 MemU SDK 异常的基类。

#### MemuAPIException
API 相关错误的异常。

**属性**:
- `status_code`: HTTP 状态码
- `response_data`: 响应数据

#### MemuValidationException
数据验证错误的异常（继承自 MemuAPIException）。

#### MemuAuthenticationException
认证错误的异常（继承自 MemuAPIException）。

#### MemuConnectionException
连接错误的异常。

### 错误处理示例

```python
from memu.sdk import MemuClient
from memu.sdk.exceptions import (
    MemuAPIException,
    MemuValidationException,
    MemuAuthenticationException,
    MemuConnectionException
)

try:
    client = MemuClient(base_url="https://api.memu.ai", api_key="your-key")
    response = client.memorize_conversation(
        conversation_text="Hello world",
        user_id="user1",
        user_name="Alice", 
        agent_id="agent1",
        agent_name="Bot",
        project_id="proj1"
    )
except MemuValidationException as e:
    print(f"Validation error: {e}")
    print(f"Details: {e.response_data}")
except MemuAuthenticationException as e:
    print(f"Auth error: {e}")
except MemuConnectionException as e:
    print(f"Connection error: {e}")
except MemuAPIException as e:
    print(f"API error: {e} (Status: {e.status_code})")
```

## 环境变量

SDK 支持以下环境变量：

- `MEMU_API_BASE_URL`: API 服务器基础 URL
- `MEMU_API_KEY`: API 密钥

## 配置选项

### 超时设置

```python
client = MemuClient(
    base_url="https://api.memu.ai",
    api_key="your-key",
    timeout=60.0  # 60 秒超时
)
```

### 重试配置

```python
client = MemuClient(
    base_url="https://api.memu.ai", 
    api_key="your-key",
    max_retries=5  # 最多重试 5 次
)
```

### 自定义 Headers

```python
client = MemuClient(
    base_url="https://api.memu.ai",
    api_key="your-key",
    headers={
        "Custom-Header": "custom-value",
        "X-Client-Version": "1.0.0"
    }
)
```

## 最佳实践

1. **使用上下文管理器**: 确保客户端资源正确清理
2. **设置适当的超时**: 根据网络条件调整超时时间
3. **处理异常**: 实现完整的错误处理逻辑
4. **使用环境变量**: 避免在代码中硬编码敏感信息
5. **日志记录**: 启用日志来调试问题

## 示例代码

完整的使用示例请参考 `example/sdk_example.py` 文件。

## 支持

如有问题或建议，请提交 Issue 到 [GitHub 仓库](https://github.com/NevaMind-AI/MemU)。