# PersonaLab 数据库结构文档

## 概述

PersonaLab 使用 **PostgreSQL + pgvector** 作为数据库系统，用于存储对话、记忆和向量嵌入数据，支持智能对话、记忆保持、语义搜索和个性化AI代理服务。

## 数据库系统配置

- **数据库类型**: PostgreSQL 15 + pgvector扩展
- **数据库名**: personalab
- **默认用户**: personalab / chenhong
- **默认端口**: 5432
- **向量维度**: 1536 (OpenAI embedding 标准维度)

## 数据库表结构

### 1. memories 表（记忆主表）

**作用**: 存储AI代理的记忆元数据和概要信息，每个代理-用户组合对应一条记录。

```sql
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 3,

    -- Embedded content for simplified access
    profile_content JSONB,
    event_content JSONB,
    mind_content JSONB,

    -- Memory statistics
    profile_content_hash TEXT,
    last_event_date TIMESTAMP,

    -- Unique constraint for agent-user combination
    UNIQUE(agent_id, user_id)
);
```

| 字段名 | 数据类型 | 约束 | 作用说明 |
|--------|----------|------|----------|
| memory_id | TEXT | PRIMARY KEY | 记忆的唯一标识符 |
| agent_id | TEXT | NOT NULL | 所属代理的唯一标识符 |
| user_id | TEXT | NOT NULL | 关联用户的唯一标识符 |
| created_at | TIMESTAMP | NOT NULL | 记忆创建时间戳 |
| updated_at | TIMESTAMP | NOT NULL | 记忆最后更新时间戳 |
| version | INTEGER | DEFAULT 3 | 记忆版本号，用于数据迁移 |
| profile_content | JSONB | - | 简化访问的配置文件内容（JSON格式） |
| event_content | JSONB | - | 简化访问的事件内容（JSON格式） |
| mind_content | JSONB | - | 简化访问的心理状态内容（JSON格式） |
| profile_content_hash | TEXT | - | 配置文件内容的哈希值，用于重复检测 |
| last_event_date | TIMESTAMP | - | 最后一个事件的日期 |

**约束**:
- **主键**: memory_id
- **唯一约束**: (agent_id, user_id) - 确保每个代理-用户组合只有一个记忆记录

### 2. memory_contents 表（记忆内容详情表）

**作用**: 存储记忆的详细内容和向量嵌入，支持语义搜索。每条记忆可以有多种类型的内容（profile、event、mind）。

```sql
CREATE TABLE IF NOT EXISTS memory_contents (
    content_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('profile', 'event', 'mind')),

    -- Content data
    content_data JSONB NOT NULL,
    content_text TEXT,
    content_hash TEXT,

    -- Vector embedding for semantic search
    content_vector vector(1536),  -- Default OpenAI embedding dimension

    -- Metadata
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE,
    UNIQUE(memory_id, content_type)
);
```

| 字段名 | 数据类型 | 约束 | 作用说明 |
|--------|----------|------|----------|
| content_id | TEXT | PRIMARY KEY | 内容的唯一标识符 |
| memory_id | TEXT | NOT NULL, FOREIGN KEY | 关联的记忆ID |
| content_type | TEXT | NOT NULL, CHECK | 内容类型：'profile'（档案）、'event'（事件）、'mind'（心理状态） |
| content_data | JSONB | NOT NULL | 结构化的内容数据 |
| content_text | TEXT | - | 纯文本格式的内容，用于搜索 |
| content_hash | TEXT | - | 内容哈希值，用于重复检测 |
| content_vector | vector(1536) | - | OpenAI嵌入向量（1536维），用于语义搜索 |
| created_at | TIMESTAMP | NOT NULL | 内容创建时间戳 |
| updated_at | TIMESTAMP | NOT NULL | 内容最后更新时间戳 |

**约束**:
- **主键**: content_id
- **外键**: memory_id 引用 memories(memory_id)，级联删除
- **唯一约束**: (memory_id, content_type) - 确保每个记忆每种类型只有一个内容记录
- **检查约束**: content_type 必须是 'profile'、'event' 或 'mind' 之一

### 3. conversations 表（对话主表）

**作用**: 存储对话会话的元数据和处理结果，包含完整的对话历史。所有消息数据直接存储在 conversation_data 字段中。

```sql
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    conversation_data JSONB NOT NULL,
    pipeline_result JSONB,
    memory_id TEXT,
    session_id TEXT,
    conversation_vector vector(1536)  -- For conversation-level embeddings
);
```

| 字段名 | 数据类型 | 约束 | 作用说明 |
|--------|----------|------|----------|
| conversation_id | TEXT | PRIMARY KEY | 对话的唯一标识符 |
| agent_id | TEXT | NOT NULL | 参与对话的代理ID |
| user_id | TEXT | NOT NULL | 参与对话的用户ID |
| created_at | TIMESTAMP | NOT NULL | 对话创建时间戳 |
| conversation_data | JSONB | NOT NULL | 完整的对话数据（包含所有消息的详细信息） |
| pipeline_result | JSONB | - | 对话处理管道的结果数据 |
| memory_id | TEXT | - | 关联的记忆ID |
| session_id | TEXT | - | 会话标识符，用于分组相关对话 |
| conversation_vector | vector(1536) | - | 对话级别的向量嵌入，用于对话搜索 |

**约束**:
- **主键**: conversation_id

## 数据库索引

### memories 表索引
```sql
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_agent_user ON memories(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at);
```

### memory_contents 表索引
```sql
CREATE INDEX IF NOT EXISTS idx_memory_contents_memory_type ON memory_contents(memory_id, content_type);
CREATE INDEX IF NOT EXISTS idx_memory_contents_hash ON memory_contents(content_hash);
CREATE INDEX IF NOT EXISTS idx_memory_contents_vector_hnsw ON memory_contents USING hnsw (content_vector vector_cosine_ops);
```

### conversations 表索引
```sql
CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_vector_hnsw ON conversations USING hnsw (conversation_vector vector_cosine_ops);
```

## 向量搜索说明

项目使用 **pgvector** 扩展来存储和搜索高维向量：

- **向量维度**: 1536 (OpenAI text-embedding-ada-002 标准维度)
- **索引类型**: HNSW (Hierarchical Navigable Small World)
- **相似度算法**: 余弦相似度 (vector_cosine_ops)
- **应用场景**: 
  - 记忆内容语义搜索
  - 对话历史相似性匹配
  - 跨会话的语义关联分析

## 核心功能支持

### 1. 记忆管理
- **存储**: AI代理的长期记忆（个人档案、事件历史、心理状态）
- **检索**: 基于代理ID和用户ID的快速查询
- **更新**: 增量更新记忆内容，保持版本控制
- **语义搜索**: 通过向量嵌入实现内容的语义检索

### 2. 对话历史
- **完整保存**: 用户与AI代理的所有对话记录存储在单一JSONB字段中
- **会话管理**: 通过session_id分组相关对话
- **简化结构**: 所有消息信息集中存储，减少表间关联查询
- **语义搜索**: 对话级别的向量嵌入支持相似对话查找

### 3. 语义搜索
- **向量嵌入**: 自动生成内容的向量表示
- **相似度搜索**: 基于语义相似度的内容检索
- **双级搜索**: 支持记忆级别和对话级别搜索

### 4. 数据完整性
- **外键约束**: 确保数据关系一致性
- **唯一约束**: 防止重复记录
- **级联删除**: 自动清理关联数据

### 5. 性能优化
- **复合索引**: 优化多字段查询性能
- **HNSW索引**: 高效的向量相似度搜索
- **简化架构**: 减少表间关联，提高查询效率
- **JSONB优化**: 利用PostgreSQL的JSONB高效存储和查询能力

## 数据流程

### 记忆保存流程
1. 在 `memories` 表中创建/更新记忆元数据
2. 在 `memory_contents` 表中保存具体内容和向量
3. 更新统计信息（最后更新时间、内容哈希等）

### 对话保存流程
1. 在 `conversations` 表中保存完整对话数据（包含所有消息）
2. 生成并保存对话级别的向量嵌入
3. 关联相应的记忆和会话信息

### 搜索流程
1. 将查询文本转换为向量嵌入
2. 使用向量相似度搜索相关内容
3. 结合元数据筛选和排序结果

## 数据结构说明

### conversation_data JSON结构
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

### memory content_data JSON结构
```json
{
  "profile": ["个人档案信息1", "个人档案信息2"],
  "event": ["事件记录1", "事件记录2"],
  "mind": ["心理状态分析1", "心理状态分析2"]
}
```

## 环境配置

### Docker 配置
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: personalab
      POSTGRES_USER: personalab
      POSTGRES_PASSWORD: personalab
    ports:
      - "5432:5432"
```

### 环境变量
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=personalab
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""
```

## 维护说明

### 数据库初始化
- 自动创建表结构和索引
- 启用 pgvector 扩展
- 注册向量类型

### 数据迁移
- 通过 `version` 字段支持版本控制
- 向后兼容的数据结构升级

### 性能监控
- 定期检查索引使用情况
- 监控向量搜索性能
- 优化JSONB查询计划

## 设计优势

### 简化架构
- **减少表数量**: 从4张表简化为3张表
- **集中存储**: 对话消息集中在conversation_data中
- **减少JOIN**: 降低复杂查询的性能开销

### 灵活性提升
- **JSONB优势**: 利用PostgreSQL原生JSON支持
- **模式演进**: 更容易适应业务需求变化
- **查询灵活**: 支持复杂的JSON查询语法

### 维护简化
- **数据一致性**: 减少跨表约束
- **备份恢复**: 数据结构更加紧凑
- **扩展性**: 更容易添加新的字段和功能

---

*该文档基于 PersonaLab 项目的简化数据库实现，专注于核心功能和性能优化。* 