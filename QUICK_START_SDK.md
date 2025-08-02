# MemU Python SDK 快速开始指南

## 安装

```bash
pip install memu-py
```

## 基本使用

### 1. 环境设置

```bash
export MEMU_API_BASE_URL="https://your-memu-api-server.com"
export MEMU_API_KEY="your-api-key-here"
```

### 2. 简单示例

```python
from memu.sdk import MemuClient

# 使用环境变量初始化客户端
with MemuClient() as client:
    # 记忆化对话
    response = client.memorize_conversation(
        conversation_text="User: I love hiking in mountains. Assistant: That sounds amazing! What's your favorite trail?",
        user_id="user_123",
        user_name="Alice Johnson",
        agent_id="agent_456", 
        agent_name="AI Assistant",
        project_id="project_789"
    )
    
    print(f"✅ 任务创建成功！")
    print(f"📋 任务 ID: {response.task_id}")
    print(f"📊 状态: {response.status}")
    print(f"💬 消息: {response.message}")
```

### 3. 完整示例

```python
from memu.sdk import MemuClient
from memu.sdk.exceptions import MemuAPIException, MemuValidationException

try:
    # 显式指定参数
    client = MemuClient(
        base_url="https://api.memu.ai",
        api_key="your-api-key",
        timeout=60.0,
        max_retries=3
    )
    
    # 批量处理多个对话
    conversations = [
        {
            "conversation_text": "User: 今天天气怎么样？Assistant: 今天天气晴朗，温度22°C。",
            "user_id": "user_001",
            "user_name": "张三",
            "agent_id": "weather_bot",
            "agent_name": "天气助手",
            "project_id": "weather_app"
        },
        {
            "conversation_text": "User: 推荐一本好书。Assistant: 我推荐《Python编程：从入门到实践》。",
            "user_id": "user_002", 
            "user_name": "李四",
            "agent_id": "book_bot",
            "agent_name": "图书推荐助手",
            "project_id": "library_app"
        }
    ]
    
    task_ids = []
    for conv in conversations:
        response = client.memorize_conversation(**conv)
        task_ids.append(response.task_id)
        print(f"✅ 为 {conv['user_name']} 创建任务: {response.task_id}")
    
    print(f"📊 总共创建了 {len(task_ids)} 个任务")
    
except MemuValidationException as e:
    print(f"❌ 数据验证错误: {e}")
    print(f"   详细信息: {e.response_data}")
except MemuAPIException as e:
    print(f"❌ API 错误: {e}")
    print(f"   状态码: {e.status_code}")
except Exception as e:
    print(f"❌ 其他错误: {e}")
finally:
    client.close()
```

## API 参考

### MemuClient

| 参数 | 类型 | 描述 | 默认值 |
|------|------|------|--------|
| base_url | str | API 服务器地址 | 环境变量 MEMU_API_BASE_URL |
| api_key | str | API 密钥 | 环境变量 MEMU_API_KEY |
| timeout | float | 请求超时时间（秒） | 30.0 |
| max_retries | int | 最大重试次数 | 3 |

### memorize_conversation

记忆化对话的主要方法。

| 参数 | 类型 | 描述 | 必需 |
|------|------|------|------|
| conversation_text | str | 对话文本内容 | ✅ |
| user_id | str | 用户唯一标识 | ✅ |
| user_name | str | 用户显示名称 | ✅ |
| agent_id | str | 代理唯一标识 | ✅ |
| agent_name | str | 代理显示名称 | ✅ |
| project_id | str | 项目唯一标识 | ✅ |
| api_key_id | str | API 密钥标识 | ❌ |

### 响应格式

```python
class MemorizeResponse:
    task_id: str     # Celery 任务 ID，用于追踪处理状态
    status: str      # 任务状态（如 "pending", "processing", "completed"）
    message: str     # 响应消息
```

## 异常处理

| 异常类型 | 描述 | 何时抛出 |
|----------|------|----------|
| MemuValidationException | 数据验证错误 | 请求参数不符合要求 |
| MemuAuthenticationException | 认证错误 | API 密钥无效或过期 |
| MemuConnectionException | 连接错误 | 网络连接失败 |
| MemuAPIException | API 错误 | 其他 API 相关错误 |

## 更多示例

查看完整示例：
- [基础用法示例](example/sdk_example.py)
- [详细文档](memu/sdk/README.md)
- [测试用例](tests/test_sdk.py)

## 支持

- GitHub Issues: [提交问题](https://github.com/NevaMind-AI/MemU/issues)
- Discord: [加入社区](https://discord.gg/hQZntfGsbJ)
- Email: support@nevamind.ai