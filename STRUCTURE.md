# AI Memory Framework - 架构设计文档

## 1. 核心Memory类设计

### 1.1 Memory统一类
Memory是Agent记忆系统的核心类，内部集成ProfileMemory和EventMemory两个组件，为Agent提供完整的记忆管理功能。

**基本属性：**
- memory_id: 唯一标识符
- agent_id: 关联的Agent ID
- created_at: 创建时间
- updated_at: 更新时间

**核心组件：**
- profile_memory: ProfileMemory实例（画像记忆）
- event_memory: EventMemory实例（事件记忆）

**核心方法：**
- get_profile_content(): 获取画像记忆内容
- get_event_content(): 获取事件记忆内容
- update_profile(): 更新画像记忆
- update_events(): 更新事件记忆
- to_prompt(): 将完整记忆转换为prompt格式
- to_dict(): 转换为字典格式

### 1.2 ProfileMemory（画像记忆组件）
作为Memory类的内部组件，用于存储用户或Agent的画像信息。

**存储格式：** 单个paragraph（段落）形式

**特点：**
- 内容结构化为一个连贯的段落
- 描述用户的基本信息、偏好、特征等
- 相对稳定，更新频率较低
- 支持增量更新和信息合并

**典型内容示例：**
```
用户是一名18岁的男性学生，喜欢玩游戏，特别是RPG类型的游戏。
平时比较内向，但对科技和编程很感兴趣。住在北京，正在学习计算机科学专业。
```

**核心方法：**
- get_content(): 获取画像内容
- update_content(new_info): 更新画像信息
- to_prompt(): 转换为prompt格式

### 1.3 EventMemory（事件记忆组件）
作为Memory类的内部组件，用于存储具体的事件或对话记录。

**存储格式：** list of paragraphs（段落列表）形式

**特点：**
- 内容结构化为多个段落的列表
- 每个段落描述事件的一个方面或时间点
- 动态变化，可以添加新的段落
- 支持时间序列的事件记录
- 自动管理事件容量（如保留最近N个事件）

**典型内容示例：**
```
[
  "昨天用户去了迪士尼乐园游玩。",
  "上午10点进入园区，首先体验了太空山项目。", 
  "中午在城堡餐厅用餐，点了米奇造型的汉堡。",
  "下午观看了花车巡游，拍了很多照片。",
  "晚上8点观看了烟花表演后离开。"
]
```

**核心方法：**
- get_content(): 获取事件列表
- add_event(event_paragraph): 添加新事件
- update_recent_events(events): 更新最近事件
- to_prompt(): 转换为prompt格式

### 1.4 Memory类接口设计

**Memory统一类接口：**
- `__init__(agent_id, memory_id)`: 初始化Memory对象
- `get_profile_content()`: 获取画像记忆内容
- `get_event_content()`: 获取事件记忆内容
- `update_profile(new_info)`: 更新画像记忆
- `update_events(new_events)`: 更新事件记忆
- `to_prompt()`: 转换为完整prompt格式
- `to_dict()`: 转换为字典格式

**ProfileMemory组件接口：**
- `get_content()`: 获取画像内容
- `update_content(new_info)`: 更新画像信息（支持智能合并）
- `to_prompt()`: 转换为prompt格式

**EventMemory组件接口：**
- `get_content()`: 获取事件列表
- `add_event(event)`: 添加新事件
- `update_recent_events(events)`: 批量更新事件
- `to_prompt()`: 转换为prompt格式
- 自动容量管理（保留最近N个事件）

### 1.5 新的类关系图
```
Memory (统一记忆类)
├── profile_memory: ProfileMemory
│   └── content: paragraph (string)
├── event_memory: EventMemory
│   └── events: list of paragraphs (list[string])
└── 统一接口方法
    ├── get_profile_content()
    ├── get_event_content()
    ├── update_profile()
    ├── update_events()
    └── to_prompt()
```

### 1.6 使用示例

**基本使用流程：**
1. 创建Memory实例：`memory = Memory(agent_id="agent_123")`
2. 更新画像记忆：`memory.update_profile("用户基本信息")`
3. 更新事件记忆：`memory.update_events(["事件1", "事件2"])`
4. 获取prompt上下文：`context = memory.to_prompt()`

**输出格式示例：**
```
## 用户画像
用户是18岁男学生，喜欢游戏和编程

## 相关事件
- 用户今天询问了Python编程问题
- 用户表示想要学习游戏开发
- 用户分享了自己的项目想法
```

## 2. Memory更新Pipeline

### 2.1 更新Pipeline概述
Memory的更新通过一个三阶段的pipeline实现：Modification → Update → Theory of Mind

```
Input   →  Modification → Update  → Theory of Mind → Database Storage
  ↓             ↓          ↓            ↓                  ↓
新对话+旧记忆   更新信息   记忆全量更新     心理建模          持久化存储
```

### 2.2 Pipeline阶段详解

#### 2.2.1 Modification阶段
**功能：** 对新输入的信息进行预处理和格式化

**处理内容：**
- 信息清洗和标准化
- 内容验证和安全检查
- 格式转换（转换为适合存储的格式）
- 时间戳添加和元数据提取

**输入：** 原始信息（文本、对话等）
**输出：** 结构化的信息对象

#### 2.2.2 Update阶段
**功能：** 将新信息与现有记忆进行合并和更新

**处理逻辑：**
- **ProfileMemory更新：** 
  - 检测与现有画像的冲突或补充
  - 合并新信息到现有段落
  - 解决信息矛盾（新信息优先级判断）
- **EventMemory更新：**
  - 添加新的事件段落
  - 按时间序列排序
  - 合并相关的事件信息

**输入：** 结构化信息 + 现有Memory对象
**输出：** 更新后的Memory对象

#### 2.2.3 Theory of Mind阶段
**功能：** 基于心理理论对记忆进行深度分析和推理

**分析维度：**
- **意图推理：** 分析用户行为背后的动机和目标
- **情绪状态：** 识别和记录用户的情绪变化
- **认知模式：** 理解用户的思维方式和决策模式
- **社交关系：** 分析用户与他人的互动模式
- **长期趋势：** 识别用户行为和偏好的变化趋势

**输出增强：**
- 为Memory添加心理学标签和元数据
- 生成推理结果和置信度
- 建立Memory之间的关联关系

### 2.3 更新函数接口

**Memory.update_with_pipeline(previous_memory, session_conversation)**
```
参数：
- previous_memory: 之前的Memory对象（包含ProfileMemory和EventMemory组件）
- session_conversation: 当前会话的对话内容

返回：
- new_memory: 更新后的新Memory对象
- pipeline_result: Pipeline执行结果和元数据

处理流程：
1. modification_result = self.modification_stage(session_conversation)
2. profile_update_result = self.update_profile_stage(previous_memory.profile_memory, modification_result)
3. event_update_result = self.update_event_stage(previous_memory.event_memory, modification_result)  
4. tom_result = self.theory_of_mind_stage(profile_update_result, event_update_result)
5. new_memory = self.create_updated_memory(previous_memory, tom_result)
6. self.save_conversation_to_database(session_conversation)
7. self.save_memory_to_database(new_memory)
8. return new_memory, pipeline_result
```

**更新策略概要：**
1. **Modification阶段**：预处理对话内容，提取画像相关信息和事件信息
2. **Profile Update阶段**：判断是否包含用户新信息，如有则更新画像记忆
3. **Event Update阶段**：将对话转换为事件段落，添加到事件记忆
4. **Theory of Mind阶段**：对更新后的记忆进行深度分析和推理
5. **保存阶段**：保存更新后的Memory对象和会话记录

**更新示例：**
- **输入**：已有Memory + 新的对话内容
- **处理**：通过Pipeline分析和更新画像、事件记忆
- **输出**：更新后的Memory对象 + Pipeline执行结果

## 3. 数据库存储设计

### 3.1 存储架构
Memory对象持久化存储在数据库中，采用统一的Memory表设计，支持高效的查询和更新操作。

```
数据库层
├── Memory统一表 (memories) - 存储完整的Memory对象
├── Memory内容表 (memory_contents) - 存储画像和事件内容
├── Conversation表 (conversations)
├── Conversation消息表 (conversation_messages)
├── Pipeline执行日志表 (pipeline_logs)
└── Embedding向量表 (embedding_vectors) - 用于语义搜索
```

### 3.2 核心数据表设计

#### 3.2.1 memories（统一Memory表）
```sql
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1,
    
    -- Theory of Mind 分析结果
    tom_metadata JSONB,
    confidence_score FLOAT,
    
    -- 记忆统计信息
    profile_content_hash VARCHAR(64), -- 画像内容哈希，用于变化检测
    event_count INTEGER DEFAULT 0, -- 事件数量
    last_event_date TIMESTAMP, -- 最后事件时间
    
    -- 索引和关联
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- 为常用查询创建索引
CREATE INDEX idx_memories_agent_id ON memories(agent_id);
CREATE INDEX idx_memories_updated_at ON memories(updated_at);
```

#### 3.2.2 memory_contents（Memory内容表）
```sql
CREATE TABLE memory_contents (
    content_id UUID PRIMARY KEY,
    memory_id UUID NOT NULL,
    content_type VARCHAR(20) NOT NULL, -- 'profile' or 'event'
    
    -- 内容数据
    content_data JSONB NOT NULL, -- 统一存储各种内容格式
    content_text TEXT, -- 用于全文搜索的文本内容
    content_hash VARCHAR(64), -- 内容哈希
    
    -- 元数据
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    CONSTRAINT fk_memory FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
    CONSTRAINT chk_content_type CHECK (content_type IN ('profile', 'event'))
);

-- 创建复合索引
CREATE INDEX idx_memory_contents_memory_type ON memory_contents(memory_id, content_type);
CREATE INDEX idx_memory_contents_hash ON memory_contents(content_hash);

-- 全文搜索索引
CREATE INDEX idx_memory_contents_text ON memory_contents USING gin(to_tsvector('english', content_text));
```

**Memory内容存储格式：**
```json
-- ProfileMemory内容格式
{
    "content_type": "profile",
    "content_data": {
        "paragraph": "用户是18岁男学生，喜欢游戏和编程，最近开始学习Python"
    }
}

-- EventMemory内容格式  
{
    "content_type": "event", 
    "content_data": {
        "events": [
            "用户今天询问了Python编程问题",
            "用户表示想要学习游戏开发",
            "用户分享了自己的项目想法"
        ],
        "max_events": 50
    }
}
```

#### 3.2.4 conversations（会话表）
```sql
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    session_id VARCHAR(100),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    
    -- 会话元数据
    conversation_summary TEXT,
    topics JSONB, -- 主要话题标签
    
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);
```

#### 3.2.5 conversation_messages（消息表）
```sql
CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    message_order INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- 消息元数据
    message_type VARCHAR(50), -- 'text', 'command', 'file_upload'
    metadata JSONB,
    
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
    UNIQUE(conversation_id, message_order)
);
```

#### 3.2.6 pipeline_logs（Pipeline执行日志）
```sql
CREATE TABLE pipeline_logs (
    log_id UUID PRIMARY KEY,
    memory_id UUID NOT NULL,
    conversation_id UUID, -- 关联触发更新的会话
    pipeline_stage VARCHAR(50) NOT NULL, -- 'modification', 'update', 'theory_of_mind'
    input_data JSONB,
    output_data JSONB,
    execution_time_ms INTEGER,
    status VARCHAR(20), -- 'success', 'error', 'warning'
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    
    CONSTRAINT fk_memory FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);
```

### 3.3 数据库操作接口

**基础Memory操作：**
- `save_memory(memory)`: 保存完整Memory对象到数据库
- `load_memory(memory_id)`: 从数据库加载完整Memory对象
- `load_memory_by_agent(agent_id)`: 根据Agent ID加载Memory
- `update_memory_profile(memory_id, profile_content)`: 更新画像记忆
- `update_memory_events(memory_id, events)`: 更新事件记忆
- `delete_memory(memory_id)`: 删除Memory对象

**Memory内容操作：**
- `save_memory_content(memory_id, content_type, content_data)`: 保存记忆内容
- `load_memory_contents(memory_id)`: 加载所有记忆内容
- `load_profile_content(memory_id)`: 加载画像记忆内容
- `load_event_content(memory_id)`: 加载事件记忆内容

**MemoryRepository核心操作：**
- `save_memory(memory)`: 保存Memory对象到数据库（基础信息+内容数据）
- `load_memory(memory_id)`: 加载完整Memory对象（重构Profile和Event组件）
- `load_memory_by_agent(agent_id)`: 根据Agent加载其Memory
- 支持UPSERT操作，自动处理新增和更新
- 自动计算内容哈希用于变化检测

**Conversation相关操作：**
- `save_conversation(conversation)`: 保存完整会话到数据库
- `save_conversation_message(conversation_id, message)`: 保存单条消息
- `load_conversation(conversation_id)`: 加载完整会话内容
- `get_recent_conversations(agent_id, limit)`: 获取最近的会话列表

**Pipeline相关操作：**
- `log_pipeline_execution(memory_id, conversation_id, stage, result)`: 记录Pipeline执行日志
- `get_pipeline_history(memory_id)`: 获取Memory的更新历史
- `rollback_memory(memory_id, version)`: 回滚到指定版本

### 3.4 数据流示例

**完整的Memory更新流程：**
```
1. 用户与AI进行对话
   ↓
2. 会话结束，conversation保存到数据库
   ↓
3. 根据agent_id加载previous_memory（包含profile和event组件）
   ↓
4. 调用update_with_pipeline(previous_memory, session_conversation)
   ↓
5. Pipeline执行：
   - modification → 预处理对话内容
   - profile_update → 更新画像记忆组件
   - event_update → 更新事件记忆组件
   - theory_of_mind → 深度分析和推理
   ↓
6. 生成updated_memory并保存到数据库
   - 保存到memories表（基础信息）
   - 保存到memory_contents表（画像和事件内容）
   ↓
7. 生成embedding向量用于搜索
   ↓
8. 记录pipeline_logs关联memory和conversation
```

**实际使用流程：**
1. **加载或创建Memory**：根据agent_id加载现有Memory或创建新Memory
2. **接收对话**：获取用户与AI的对话内容
3. **Pipeline更新**：通过更新Pipeline处理对话并更新Memory
4. **保存数据**：将更新后的Memory保存到数据库
5. **更新索引**：生成embedding向量用于语义搜索
6. **结果验证**：检查更新后的画像记忆和事件记忆内容

## 4. Memory语义搜索系统

### 4.1 搜索系统概述
Memory语义搜索系统通过embedding技术实现对历史对话和记忆内容的语义检索，支持自然语言查询找到相关的conversation和memory记录。

**核心功能：**
- 基于语义相似度的conversation检索
- Memory内容的相关性搜索
- 多模态搜索（文本、时间、主题等维度）
- 实时搜索和缓存优化

### 4.2 搜索架构设计

```
查询输入 → 查询处理 → 向量检索 → 相关性排序 → 结果返回
   ↓         ↓        ↓        ↓         ↓
自然语言   embedding  向量数据库  评分算法   结构化结果
```

#### 4.2.1 向量存储设计
**embedding_vectors表：**
```sql
CREATE TABLE embedding_vectors (
    vector_id UUID PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL, -- 'conversation', 'message', 'memory'
    content_id UUID NOT NULL, -- 关联到具体内容的ID
    agent_id UUID NOT NULL,
    
    -- 向量数据
    embedding_vector VECTOR(1536), -- OpenAI text-embedding-ada-002 dimension
    embedding_model VARCHAR(100) NOT NULL, -- 'text-embedding-ada-002'
    
    -- 内容元数据
    content_text TEXT NOT NULL, -- 原始文本内容
    content_summary TEXT, -- 内容摘要
    tokens_count INTEGER,
    
    -- 时间和版本
    created_at TIMESTAMP NOT NULL,
    last_updated TIMESTAMP NOT NULL,
    
    -- 索引
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- 向量相似度搜索索引
CREATE INDEX idx_embedding_vectors_cosine ON embedding_vectors 
USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);
```

#### 4.2.2 搜索索引表
**search_indexes表：**
```sql
CREATE TABLE search_indexes (
    index_id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    
    -- 搜索元数据
    keywords JSONB, -- 提取的关键词
    topics JSONB, -- 主题标签
    sentiment_score FLOAT, -- 情感分析分数
    importance_score FLOAT, -- 重要性评分
    
    -- 时间维度
    content_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- 全文搜索索引
CREATE INDEX idx_search_keywords ON search_indexes USING GIN (keywords);
CREATE INDEX idx_search_topics ON search_indexes USING GIN (topics);
```

### 4.3 搜索功能实现

#### 4.3.1 MemorySearcher类接口
**核心搜索方法：**
- `search_conversations(query, limit, time_range, similarity_threshold)`: 搜索相关对话记录
- `search_memories(query, memory_types, limit)`: 搜索相关记忆内容  
- `hybrid_search(query, weights)`: 混合搜索（语义+关键词+时间权重）

**搜索参数：**
- **query**: 自然语言搜索查询
- **limit**: 返回结果数量限制
- **time_range**: 时间范围筛选
- **similarity_threshold**: 相似度阈值
- **memory_types**: 记忆类型过滤（profile/event）

#### 4.3.2 搜索算法概要

**核心算法组件：**
1. **语义相似度计算**：使用余弦相似度计算查询与内容的语义相关性
2. **综合评分算法**：结合语义、关键词、时间、重要性等多维度评分
3. **时间衰减函数**：近期内容获得更高权重，使用指数衰减函数
4. **结果排序优化**：基于综合评分排序并进行结果去重和多样性优化
