# AI Memory Framework - 架构设计文档

## 1. 核心Memory类设计

### 1.1 Memory抽象类
Memory是所有记忆类型的基础抽象类，定义了记忆的通用接口和基本属性。

**基本属性：**
- memory_id: 唯一标识符
- created_at: 创建时间
- updated_at: 更新时间

**核心方法：**
- get_content(): 获取记忆内容
- update_content(): 更新记忆内容
- to_dict(): 转换为字典格式
- to_prompt(): 将记忆转换为string prompt格式

### 1.2 ProfileMemory（画像记忆）
继承自Memory抽象类，用于存储用户或Agent的画像信息。

**存储格式：** 单个paragraph（段落）形式

**特点：**
- 内容结构化为一个连贯的段落
- 描述用户的基本信息、偏好、特征等
- 相对稳定，更新频率较低

**典型内容示例：**
```
用户是一名18岁的男性学生，喜欢玩游戏，特别是RPG类型的游戏。
平时比较内向，但对科技和编程很感兴趣。住在北京，正在学习计算机科学专业。
```

**to_prompt()输出格式：**
```
## 用户画像
用户是一名18岁的男性学生，喜欢玩游戏，特别是RPG类型的游戏。
平时比较内向，但对科技和编程很感兴趣。住在北京，正在学习计算机科学专业。
```

### 1.3 EventMemory（事件记忆）
继承自Memory抽象类，用于存储具体的事件或对话记录。

**存储格式：** list of paragraphs（段落列表）形式

**特点：**
- 内容结构化为多个段落的列表
- 每个段落描述事件的一个方面或时间点
- 动态变化，可以添加新的段落
- 支持时间序列的事件记录

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

**to_prompt()输出格式：**
```
## 相关事件
- 昨天用户去了迪士尼乐园游玩。
- 上午10点进入园区，首先体验了太空山项目。
- 中午在城堡餐厅用餐，点了米奇造型的汉堡。
- 下午观看了花车巡游，拍了很多照片。
- 晚上8点观看了烟花表演后离开。
```

### 1.4 类关系图
```
Memory (抽象类)
├── ProfileMemory
│   └── content: paragraph (string)
└── EventMemory
    └── content: list of paragraphs (list[string])
```

## 2. Memory更新Pipeline

### 2.1 更新Pipeline概述
Memory的更新通过一个三阶段的pipeline实现：Modification → Update → Theory of Mind

```
Input → Modification → Update → Theory of Mind → Database Storage
  ↓          ↓          ↓            ↓              ↓
新信息    信息处理    记忆合并    心理建模      持久化存储
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
- previous_memory: 之前的Memory对象（ProfileMemory或EventMemory）
- session_conversation: 当前会话的对话内容

返回：
- new_memory: 更新后的新Memory对象
- pipeline_result: Pipeline执行结果和元数据

处理流程：
1. modification_result = self.modification_stage(session_conversation)
2. update_result = self.update_stage(previous_memory, modification_result)  
3. tom_result = self.theory_of_mind_stage(update_result)
4. new_memory = self.create_new_memory(tom_result)
5. self.save_conversation_to_database(session_conversation)
6. self.save_memory_to_database(new_memory)
7. return new_memory, pipeline_result
```

**示例调用：**
```
# ProfileMemory更新示例
previous_profile = ProfileMemory("用户是18岁男学生，喜欢游戏")
conversation = [
    {"role": "user", "content": "我最近开始学习Python编程"},
    {"role": "assistant", "content": "很好！Python是很适合初学者的语言"},
    {"role": "user", "content": "我想做一个游戏项目"}
]

new_profile, result = previous_profile.update_with_pipeline(previous_profile, conversation)
# new_profile.content: "用户是18岁男学生，喜欢游戏，最近开始学习Python编程，想做游戏项目"
```

## 3. 数据库存储设计

### 3.1 存储架构
Memory对象持久化存储在数据库中，支持高效的查询和更新操作。

```
数据库层
├── Memory基础表 (memories)
├── ProfileMemory扩展表 (profile_memories)  
├── EventMemory扩展表 (event_memories)
├── Memory关系表 (memory_relationships)
├── Conversation表 (conversations)
├── Conversation消息表 (conversation_messages)
└── Pipeline执行日志表 (pipeline_logs)
```

### 3.2 核心数据表设计

#### 3.2.1 memories（基础表）
```sql
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY,
    memory_type VARCHAR(50) NOT NULL, -- 'profile' or 'event'
    agent_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1,
    
    -- Theory of Mind 分析结果
    tom_metadata JSONB,
    confidence_score FLOAT,
    
    -- 索引和关联
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);
```

#### 3.2.2 profile_memories（画像记忆表）
```sql
CREATE TABLE profile_memories (
    memory_id UUID PRIMARY KEY,
    profile_content TEXT NOT NULL,
    content_hash VARCHAR(64), -- 用于去重
    
    CONSTRAINT fk_memory FOREIGN KEY (memory_id) REFERENCES memories(memory_id)
);
```

#### 3.2.3 event_memories（事件记忆表）
```sql
CREATE TABLE event_memories (
    memory_id UUID PRIMARY KEY,
    event_paragraphs JSONB NOT NULL, -- 存储段落数组
    paragraph_count INTEGER NOT NULL,
    event_date TIMESTAMP,
    
    CONSTRAINT fk_memory FOREIGN KEY (memory_id) REFERENCES memories(memory_id)
);
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

**基础CRUD操作：**
- `save_memory(memory)`: 保存Memory对象到数据库
- `load_memory(memory_id)`: 从数据库加载Memory对象
- `update_memory(memory_id, updates)`: 更新特定Memory
- `delete_memory(memory_id)`: 删除Memory对象

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
3. 加载previous_memory
   ↓
4. 调用update_with_pipeline(previous_memory, session_conversation)
   ↓
5. Pipeline执行：modification → update → theory_of_mind
   ↓
6. 生成new_memory并保存到数据库
   ↓
7. 记录pipeline_logs关联memory和conversation
```

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

#### 4.3.1 MemorySearcher类
```python
class MemorySearcher:
    """Memory语义搜索引擎"""
    
    def __init__(self, agent_id: str, embedding_client: EmbeddingClient):
        self.agent_id = agent_id
        self.embedding_client = embedding_client
        self.vector_db = VectorDatabase()
        
    def search_conversations(
        self, 
        query: str, 
        limit: int = 10,
        time_range: Optional[TimeRange] = None,
        similarity_threshold: float = 0.7
    ) -> List[ConversationSearchResult]:
        """
        搜索相关的对话记录
        
        Args:
            query: 搜索查询（自然语言）
            limit: 返回结果数量限制
            time_range: 时间范围筛选
            similarity_threshold: 相似度阈值
            
        Returns:
            按相关性排序的对话搜索结果列表
        """
        
    def search_memories(
        self,
        query: str,
        memory_types: List[str] = ['profile', 'event'],
        limit: int = 5
    ) -> List[MemorySearchResult]:
        """
        搜索相关的记忆内容
        
        Args:
            query: 搜索查询
            memory_types: 记忆类型过滤
            limit: 结果数量限制
            
        Returns:
            相关记忆搜索结果列表
        """
        
    def hybrid_search(
        self,
        query: str,
        include_conversations: bool = True,
        include_memories: bool = True,
        time_weight: float = 0.1,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.2
    ) -> HybridSearchResult:
        """
        混合搜索：结合语义搜索、关键词搜索和时间权重
        """
```

#### 4.3.2 搜索算法详解

**1. 语义相似度计算：**
```python
def calculate_semantic_similarity(query_embedding, content_embedding):
    """使用余弦相似度计算语义相似度"""
    return cosine_similarity(query_embedding, content_embedding)
```

**2. 综合评分算法：**
```python
def calculate_relevance_score(
    semantic_score: float,
    keyword_score: float, 
    time_score: float,
    importance_score: float,
    weights: Dict[str, float]
) -> float:
    """
    综合相关性评分
    
    final_score = (
        semantic_score * weights['semantic'] +
        keyword_score * weights['keyword'] +
        time_score * weights['time'] +
        importance_score * weights['importance']
    )
    """
    return final_score
```
