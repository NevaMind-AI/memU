# MemU 数据格式规范

## 目录

1. [概述](#概述)
2. [Memory JSON 格式](#1-memory-json-格式)
   - 2.1 [基本结构](#11-基本结构)
   - 2.2 [数据库表结构](#12-数据库表结构)
   - 2.3 [Memory API 返回格式](#13-memory-api-返回格式)
   - 2.4 [Memory 内容类型说明](#14-memory-内容类型说明)
3. [Conversation JSON 格式](#2-conversation-json-格式)
   - 3.1 [基本结构](#21-基本结构)
   - 3.2 [数据库表结构](#22-数据库表结构)
   - 3.3 [ConversationMessage 格式](#23-conversationmessage-格式)
   - 3.4 [数据库存储格式](#24-数据库存储格式)
   - 3.5 [保存对话的 API 请求格式](#25-保存对话的-api-请求格式)
   - 3.6 [API 响应格式](#26-api-响应格式)
4. [字段说明](#3-字段说明)
   - 4.1 [必填字段](#31-必填字段)
   - 4.2 [可选字段](#32-可选字段)
   - 4.3 [消息角色 (role)](#33-消息角色-role)
   - 4.4 [pipeline_result 详细结构](#34-pipeline_result-详细结构)
   - 4.5 [对话摘要 (summary) 格式](#35-对话摘要-summary-格式)
5. [使用示例](#4-使用示例)
6. [注意事项](#5-注意事项)
7. [错误处理](#6-错误处理)
8. [性能优化](#7-性能优化)
9. [数据一致性重要说明](#8-数据一致性重要说明)
10. [版本说明](#9-版本说明)

## 概述

MemU 使用 JSON 格式来处理和存储记忆（Memory）和对话（Conversation）数据。本文档详细描述了这两种数据结构的格式规范。

## 1. Memory JSON 格式

### 1.1 基本结构

Memory 数据存储在 PostgreSQL 的 JSONB 字段中，主要包含三个核心类型：

```json
{
  "profile": ["个人档案信息1", "个人档案信息2", "..."],
  "event": ["事件记录1", "事件记录2", "..."],
  "mind": ["心理状态分析1", "心理状态分析2", "..."]
}
```

### 1.2 数据库表结构

**memories 表**：
- `memory_id` (TEXT, PRIMARY KEY): 记忆唯一标识符
- `agent_id` (TEXT, NOT NULL): 代理ID
- `user_id` (TEXT, NOT NULL): 用户ID
- `created_at` (TIMESTAMP): 创建时间
- `updated_at` (TIMESTAMP): 更新时间
- `profile_content` (JSONB): 个人档案内容
- `event_content` (JSONB): 事件内容
- `mind_content` (JSONB): 心理状态内容

**memory_contents 表**：
- `content_id` (TEXT, PRIMARY KEY): 内容唯一标识符
- `memory_id` (TEXT, FOREIGN KEY): 关联的记忆ID
- `content_type` (TEXT): 内容类型 ('profile', 'event', 'mind')
- `content_data` (JSONB): 结构化内容数据
- `content_text` (TEXT): 纯文本内容
- `content_vector` (vector(1536)): 向量嵌入（用于语义搜索）

### 1.3 Memory API 返回格式

```json
{
  "memory_id": "mem_uuid_123",
  "agent_id": "agent_001",
  "user_id": "user_001",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:30:00Z",
  "profile_content": [
    "用户是一名软件开发者",
    "擅长Python和JavaScript",
    "有5年工作经验"
  ],
  "event_content": [
    "用户参与了项目讨论",
    "用户提交了代码",
    "用户参加了会议"
  ],
  "mind_content": [
    "用户表现出积极的学习态度",
    "用户对技术细节很关注",
    "用户喜欢团队合作"
  ]
}
```

### 1.4 Memory 内容类型说明

- **profile**: 用户/代理的个人档案信息，存储为字符串数组，每个元素是一个档案条目
- **event**: 事件记录，记录用户的行为和活动，存储为字符串数组
- **mind**: 心理状态分析，记录用户的心理特征和状态，存储为字符串数组

**注意**: 在某些API接口中，profile_content 可能以字符串形式返回（通过 `\n` 连接），这是为了显示目的。在内部存储和处理时，所有内容类型都是字符串数组格式。

## 2. Conversation JSON 格式

### 2.1 基本结构

Conversation 包含对话元数据和消息列表：

```json
{
  "conversation_id": "conv_uuid_123",
  "agent_id": "agent_001",
  "user_id": "user_001",
  "session_id": "session_uuid_456",
  "created_at": "2024-01-01T10:00:00Z",
  "turn_count": 4,
  "memory_id": "mem_uuid_123",
  "messages": [
    {
      "message_id": "msg_uuid_001",
      "role": "user",
      "content": "你好，我想了解一下这个项目",
      "message_index": 0,
      "created_at": "2024-01-01T10:00:00Z"
    },
    {
      "message_id": "msg_uuid_002", 
      "role": "assistant",
      "content": "您好！我很乐意为您介绍这个项目...",
      "message_index": 1,
      "created_at": "2024-01-01T10:00:10Z"
    }
  ],
  "pipeline_result": {
    "modification_result": "LLM分析和信息提取的结果",
    "update_result": {
      "profile_updated": true,
      "raw_llm_response": "LLM原始回复",
      "metadata": {
        "stage": "llm_update",
        "updated_at": "2024-01-01T10:00:30Z"
      }
    },
    "mind_result": {
      "insights": "心理分析结果",
      "confidence_score": 0.8,
      "raw_llm_response": "LLM心理分析原始回复",
      "metadata": {
        "stage": "llm_theory_of_mind",
        "analyzed_at": "2024-01-01T10:00:40Z"
      }
    },
    "pipeline_metadata": {
      "execution_time": "2024-01-01T10:00:50Z",
      "conversation_length": 2,
      "llm_model": "gpt-4o-mini",
      "profile_updated": true
    }
  }
}
```

### 2.2 数据库表结构

**conversations 表**：
- `conversation_id` (TEXT, PRIMARY KEY): 对话唯一标识符
- `agent_id` (TEXT, NOT NULL): 代理ID
- `user_id` (TEXT, NOT NULL): 用户ID
- `created_at` (TIMESTAMP): 创建时间
- `conversation_data` (JSONB): 完整的对话数据
- `pipeline_result` (JSONB): 处理管道结果
- `memory_id` (TEXT): 关联的记忆ID
- `session_id` (TEXT): 会话ID
- `conversation_vector` (vector(1536)): 对话向量嵌入

### 2.3 ConversationMessage 格式

每条消息包含以下字段：

```json
{
  "message_id": "msg_uuid_001",
  "role": "user|assistant|system",
  "content": "消息内容",
  "message_index": 0,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### 2.4 数据库存储格式

在数据库中，对话数据存储在 `conversation_data` 字段中：

```json
{
  "messages": [
    {
      "message_id": "msg_123",
      "role": "user",
      "content": "用户消息内容",
      "message_index": 0,
      "created_at": "2024-01-01T10:00:00Z"
    },
    {
      "message_id": "msg_124", 
      "role": "assistant",
      "content": "AI助手回复内容",
      "message_index": 1,
      "created_at": "2024-01-01T10:00:10Z"
    }
  ]
}
```

### 2.5 保存对话的 API 请求格式

```json
{
  "agent_id": "agent_001",
  "user_id": "user_001",
  "messages": [
    {
      "role": "user",
      "content": "用户消息内容"
    },
    {
      "role": "assistant",
      "content": "AI助手回复内容"
    }
  ],
  "session_id": "session_uuid_456",
  "memory_id": "mem_uuid_123"
}
```

### 2.6 API 响应格式

保存成功后返回：

```json
{
  "success": true,
  "message": "Conversation saved successfully",
  "conversation_id": "conv_uuid_123",
  "session_id": "session_uuid_456",
  "created_at": "2024-01-01T10:00:00Z",
  "message_count": 2
}
```

## 3. 字段说明

### 3.1 必填字段

**Memory**:
- `memory_id`: 记忆唯一标识符
- `agent_id`: 代理ID
- `user_id`: 用户ID
- `created_at`: 创建时间
- `updated_at`: 更新时间

**Conversation**:
- `conversation_id`: 对话唯一标识符
- `agent_id`: 代理ID
- `user_id`: 用户ID
- `created_at`: 创建时间
- `messages`: 消息列表

### 3.2 可选字段

**Memory**:
- `profile_content`: 个人档案内容
- `event_content`: 事件内容
- `mind_content`: 心理状态内容
- `version`: 版本号

**Conversation**:
- `session_id`: 会话ID（如果未提供会自动生成）
- `memory_id`: 关联的记忆ID
- `pipeline_result`: 处理管道结果（包含LLM分析的详细信息）
- `summary`: 对话摘要（自动生成）

### 3.3 消息角色 (role)

- `user`: 用户消息
- `assistant`: AI助手消息
- `system`: 系统消息

### 3.4 pipeline_result 详细结构

`pipeline_result` 字段包含了记忆更新管道的完整执行结果：

```json
{
  "modification_result": "LLM分析和信息提取的结果文本",
  "update_result": {
    "profile_updated": true,
    "raw_llm_response": "LLM原始回复内容",
    "metadata": {
      "stage": "llm_update",
      "updated_at": "2024-01-01T10:00:30Z",
      "llm_usage": {
        "prompt_tokens": 1200,
        "completion_tokens": 300,
        "total_tokens": 1500
      }
    }
  },
  "mind_result": {
    "insights": "心理分析结果文本",
    "confidence_score": 0.8,
    "raw_llm_response": "LLM心理分析原始回复",
    "metadata": {
      "stage": "llm_theory_of_mind",
      "analyzed_at": "2024-01-01T10:00:40Z",
      "llm_usage": {
        "prompt_tokens": 800,
        "completion_tokens": 200,
        "total_tokens": 1000
      }
    }
  },
  "pipeline_metadata": {
    "execution_time": "2024-01-01T10:00:50Z",
    "conversation_length": 2,
    "llm_model": "gpt-4o-mini",
    "profile_updated": true
  }
}
```

**字段说明**:
- `modification_result`: 第一阶段（修改）的LLM分析结果
- `update_result`: 第二阶段（更新）的结果，包含档案和事件的更新信息
- `mind_result`: 第三阶段（心理分析）的结果，包含用户心理洞察
- `pipeline_metadata`: 管道执行的元数据，包含执行时间、模型信息等

### 3.5 对话摘要 (summary) 格式

对话摘要会自动生成，格式为：
```
"Conversation with {消息数量} turns: {第一条用户消息的前100个字符}..."
```

示例：
```
"Conversation with 4 turns: 你好，我想了解一下这个项目的功能特点..."
```

如果对话为空：
```
"Empty conversation"
```

如果没有用户消息：
```
"Conversation with 2 turns: No user message..."
```

## 4. 使用示例

### 4.1 创建 Memory 对象

```python
from memu.memory.base import Memory

memory = Memory(
    agent_id="agent_001",
    user_id="user_001",
    data={
        "profile_content": [
            "用户是一名软件开发者",
            "擅长Python和JavaScript",
            "有5年工作经验"
        ],
        "event_content": ["参与了项目讨论", "提交了代码"],
        "mind_content": ["表现出积极的学习态度"]
    }
)
```

### 4.2 创建 Conversation 对象

```python
from memu.memo.models import Conversation

conversation = Conversation(
    agent_id="agent_001",
    user_id="user_001",
    messages=[
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "您好！有什么可以帮助您的吗？"}
    ]
)
```

### 4.3 保存对话到数据库

```python
from memu.memo.manager import ConversationManager

manager = ConversationManager()
conversation = manager.record_conversation(
    agent_id="agent_001",
    user_id="user_001",
    messages=[
        {"role": "user", "content": "用户消息"},
        {"role": "assistant", "content": "助手回复"}
    ]
)
```

## 5. 注意事项

1. **时间格式**: 所有时间戳使用 ISO 8601 格式 (`YYYY-MM-DDTHH:MM:SSZ`)
2. **UUID**: 所有ID字段使用 UUID 格式
3. **向量维度**: 向量嵌入使用 1536 维度（OpenAI 标准）
4. **必填字段**: `agent_id` 和 `user_id` 是必填字段
5. **数据完整性**: 所有 JSON 数据都会进行验证
6. **编码**: 所有文本内容使用 UTF-8 编码

## 6. 错误处理

常见错误及处理：

- **缺少必填字段**: 会抛出 `ValueError`
- **JSON 解析错误**: 会记录警告并跳过无效数据
- **数据库连接错误**: 会记录错误并返回失败状态
- **向量维度不匹配**: 会重新生成向量嵌入

## 7. 性能优化

- 使用 JSONB 存储，支持高效查询
- 建立适当的索引提高查询性能
- 使用 HNSW 索引进行向量相似度搜索
- 分页查询大量数据时使用合适的限制

## 8. 数据一致性重要说明

### 8.1 数据格式统一性

- **所有内容类型** (`profile_content`, `event_content`, `mind_content`) 在内部处理时都是 **字符串数组格式**
- 在某些API接口中可能以字符串形式返回（用 `\n` 连接），这仅用于显示目的
- 数据库存储时保持原始的数组格式

### 8.2 时间戳处理

- 所有时间戳字段在数据库中存储为 PostgreSQL 的 `TIMESTAMP` 类型
- 在 JSON 序列化时转换为 ISO 8601 格式字符串
- 客户端接收到的时间戳都是 UTC 时间

### 8.3 ID 字段规范

- 所有 ID 字段 (`memory_id`, `conversation_id`, `message_id`, `agent_id`, `user_id`) 都使用字符串类型
- `memory_id`, `conversation_id`, `message_id`, `session_id` 使用 UUID 格式
- `agent_id` 和 `user_id` 可以是任意字符串，但建议使用有意义的标识符

### 8.4 向量嵌入

- 所有向量嵌入都使用 1536 维度（OpenAI text-embedding-ada-002 标准）
- 向量数据存储在 PostgreSQL 的 `vector` 类型字段中
- 支持余弦相似度搜索

### 8.5 数据完整性约束

- `agent_id` 和 `user_id` 是所有数据对象的必填字段
- 对话中的消息必须有 `role` 和 `content` 字段
- 消息索引 (`message_index`) 从 0 开始递增
- 每个 agent-user 组合只能有一个 memory 记录（唯一约束）

## 9. 版本说明

### 当前版本: v3.0

- **Memory 数据格式**: 使用三层结构 (memories表 + memory_contents表 + 向量索引)
- **Conversation 数据格式**: 单表存储，消息数据存储在 conversation_data JSONB 字段中
- **向量维度**: 1536 (OpenAI text-embedding-ada-002 标准)
- **支持的LLM模型**: GPT-4o-mini (默认), Claude-3-7-sonnet-latest (默认)

### 主要特性

1. **三阶段记忆更新管道**:
   - 阶段1: LLM修改分析
   - 阶段2: 档案和事件更新
   - 阶段3: 心理状态分析 (Theory of Mind)

2. **语义搜索能力**:
   - 支持记忆内容的向量相似度搜索
   - 支持对话内容的语义检索
   - 使用 HNSW 索引优化搜索性能

3. **数据持久化**:
   - PostgreSQL + pgvector 数据库
   - JSONB 格式存储结构化数据
   - 完整的事务支持和数据一致性保证

4. **API 接口**:
   - RESTful API 设计
   - 支持记忆的 CRUD 操作
   - 支持对话的录制和检索
   - 完整的错误处理和日志记录

---

*最后更新: 2024年1月*  
*文档版本: 1.0* 