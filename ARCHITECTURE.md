# PersonaLab Architecture Design

This document provides a comprehensive overview of the PersonaLab AI Memory Framework architecture, including design principles, component interactions, and implementation details.

## 1. Core Memory Architecture Design

### 1.1 Unified Memory Class

The `Memory` class is the core component of the PersonaLab memory system, internally integrating `ProfileMemory`, `EventMemory`, and `ToMMemory` components to provide comprehensive memory management functionality for AI agents.

**Basic Properties:**
- `memory_id`: Unique identifier for the memory instance
- `agent_id`: Associated Agent ID
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Core Components:**
- `profile_memory`: ProfileMemory instance (profile/persona memory)
- `event_memory`: EventMemory instance (event-based memory)
- `tom_memory`: ToMMemory instance (Theory of Mind insights)

**Core Methods:**
- `get_profile_content()`: Retrieve profile memory content
- `get_event_content()`: Retrieve event memory content
- `get_tom_content()`: Retrieve Theory of Mind insights
- `update_profile()`: Update profile memory
- `update_events()`: Update event memory
- `update_tom()`: Update ToM insights
- `to_prompt()`: Convert complete memory to prompt format
- `to_dict()`: Convert to dictionary format

### 1.2 ProfileMemory Component

The ProfileMemory component stores user or agent profile information as an internal component of the Memory class.

**Storage Format:** Single paragraph (string format)

**Characteristics:**
- Content structured as a coherent paragraph
- Describes basic information, preferences, characteristics, etc.
- Relatively stable, low update frequency
- Supports incremental updates and information merging

**Typical Content Example:**
```
User is an 18-year-old male student who enjoys gaming, particularly RPG games. 
Generally introverted but very interested in technology and programming. 
Lives in Beijing and is studying computer science.
```

**Core Methods:**
- `get_content()`: Retrieve profile content
- `update_content(new_info)`: Update profile information
- `to_prompt()`: Convert to prompt format

### 1.3 EventMemory Component

The EventMemory component stores specific events or conversation records as an internal component of the Memory class.

**Storage Format:** List of paragraphs (list[string] format)

**Characteristics:**
- Content structured as a list of multiple paragraphs
- Each paragraph describes an aspect or time point of events
- Dynamic changes, can add new paragraphs
- Supports time-series event recording
- Automatic event capacity management (retains recent N events)

**Typical Content Example:**
```
[
  "User visited Disneyland yesterday.",
  "Entered the park at 10 AM and first experienced Space Mountain.",
  "Had lunch at the Castle Restaurant, ordered a Mickey-shaped burger.",
  "Watched the parade in the afternoon and took many photos.",
  "Left after watching the fireworks show at 8 PM."
]
```

**Core Methods:**
- `get_content()`: Retrieve event list
- `add_event(event_paragraph)`: Add new event
- `update_recent_events(events)`: Update recent events
- `to_prompt()`: Convert to prompt format

### 1.4 ToMMemory Component

The ToMMemory component stores Theory of Mind insights and psychological analyses as an internal component of the Memory class.

**Storage Format:** List of insight paragraphs (list[string] format)

**Characteristics:**
- Content structured as psychological insights and analyses
- Each insight represents a psychological understanding or behavioral pattern
- Generated through LLM analysis of conversations and behaviors
- Supports confidence scoring and metadata attachment

**Typical Content Example:**
```
[
  "User demonstrates strong motivation for technical learning",
  "User prefers hands-on learning approaches over theoretical study",
  "User shows problem-solving persistence when facing challenges",
  "User exhibits introversion but becomes more expressive about technical topics"
]
```

**Core Methods:**
- `get_content()`: Retrieve insight list
- `add_insight(insight)`: Add new insight
- `update_insights(insights)`: Update insights
- `to_prompt()`: Convert to prompt format

### 1.5 Memory Class Interface Design

**Unified Memory Class Interface:**
- `__init__(agent_id, memory_id)`: Initialize Memory object
- `get_profile_content()`: Retrieve profile memory content
- `get_event_content()`: Retrieve event memory content
- `get_tom_content()`: Retrieve ToM memory content
- `update_profile(new_info)`: Update profile memory
- `update_events(new_events)`: Update event memory
- `update_tom(new_insights)`: Update ToM insights
- `to_prompt()`: Convert to complete prompt format
- `to_dict()`: Convert to dictionary format

**ProfileMemory Component Interface:**
- `get_content()`: Retrieve profile content
- `update_content(new_info)`: Update profile information (supports intelligent merging)
- `to_prompt()`: Convert to prompt format

**EventMemory Component Interface:**
- `get_content()`: Retrieve event list
- `add_event(event)`: Add new event
- `update_recent_events(events)`: Batch update events
- `to_prompt()`: Convert to prompt format
- Automatic capacity management (retains recent N events)

**ToMMemory Component Interface:**
- `get_content()`: Retrieve insight list
- `add_insight(insight)`: Add new insight
- `update_insights(insights)`: Update insights
- `to_prompt()`: Convert to prompt format

### 1.6 Class Relationship Diagram

```
Memory (Unified Memory Class)
├── profile_memory: ProfileMemory
│   └── content: paragraph (string)
├── event_memory: EventMemory
│   └── events: list of paragraphs (list[string])
├── tom_memory: ToMMemory
│   └── insights: list of insights (list[string])
└── Unified Interface Methods
    ├── get_profile_content()
    ├── get_event_content()
    ├── get_tom_content()
    ├── update_profile()
    ├── update_events()
    ├── update_tom()
    └── to_prompt()
```

### 1.7 Usage Examples

**Basic Usage Flow:**
1. Create Memory instance: `memory = Memory(agent_id="agent_123")`
2. Update profile memory: `memory.update_profile("User basic information")`
3. Update event memory: `memory.update_events(["Event 1", "Event 2"])`
4. Update ToM insights: `memory.update_tom(["Insight 1", "Insight 2"])`
5. Get prompt context: `context = memory.to_prompt()`

**Output Format Example:**
```
## User Profile
User is an 18-year-old male student who enjoys gaming and programming

## Related Events
- User asked about Python programming today
- User expressed interest in learning game development
- User shared project ideas

## Psychological Insights
- User demonstrates strong technical learning motivation
- User prefers practical learning approaches
- User shows collaborative tendencies in project discussions
```

## 2. Memory Update Pipeline

### 2.1 Pipeline Overview

Memory updates are implemented through a three-stage pipeline: Modification → Update → Theory of Mind

```
Input   →  Modification → Update  → Theory of Mind → Database Storage
  ↓             ↓          ↓            ↓                  ↓
New Conversation  Info Extraction  Memory Update  Psychological Analysis  Persistence
+ Previous Memory                   (Full Update)
```

### 2.2 Pipeline Stage Details

#### 2.2.1 Modification Stage
**Function:** Preprocess and format new input information

**Processing Content:**
- Information cleaning and standardization
- Content validation and safety checks
- Format conversion (convert to storage-ready format)
- Timestamp addition and metadata extraction

**Input:** Raw information (text, conversations, etc.)
**Output:** Structured information object

#### 2.2.2 Update Stage
**Function:** Merge new information with existing memory

**Processing Logic:**
- **ProfileMemory Update:**
  - Detect conflicts or supplements with existing profile
  - Merge new information into existing paragraphs
  - Resolve information conflicts (new information priority judgment)
- **EventMemory Update:**
  - Add new event paragraphs
  - Sort by time sequence
  - Merge related event information

**Input:** Structured information + existing Memory object
**Output:** Updated Memory object

#### 2.2.3 Theory of Mind Stage
**Function:** Perform deep analysis and reasoning based on psychological theory

**Analysis Dimensions:**
- **Intent Inference:** Analyze motivations and goals behind user behavior
- **Emotional State:** Identify and record user emotional changes
- **Cognitive Patterns:** Understand user thinking patterns and decision-making modes
- **Social Relationships:** Analyze user interaction patterns with others
- **Long-term Trends:** Identify changes in user behavior and preferences

**Output Enhancement:**
- Add psychological tags and metadata to Memory
- Generate reasoning results and confidence scores
- Establish associative relationships between Memories

### 2.3 Update Function Interface

**Memory.update_with_pipeline(previous_memory, session_conversation)**
```
Parameters:
- previous_memory: Previous Memory object (including ProfileMemory, EventMemory, and ToMMemory components)
- session_conversation: Current session conversation content

Returns:
- new_memory: Updated new Memory object
- pipeline_result: Pipeline execution results and metadata

Processing Flow:
1. modification_result = self.modification_stage(session_conversation)
2. profile_update_result = self.update_profile_stage(previous_memory.profile_memory, modification_result)
3. event_update_result = self.update_event_stage(previous_memory.event_memory, modification_result)
4. tom_result = self.theory_of_mind_stage(profile_update_result, event_update_result)
5. new_memory = self.create_updated_memory(previous_memory, tom_result)
6. self.save_conversation_to_database(session_conversation)
7. self.save_memory_to_database(new_memory)
8. return new_memory, pipeline_result
```

**Update Strategy Summary:**
1. **Modification Stage**: Preprocess conversation content, extract profile-related information and event information
2. **Profile Update Stage**: Determine if new user information is included, update profile memory if present
3. **Event Update Stage**: Convert conversation to event paragraphs, add to event memory
4. **Theory of Mind Stage**: Perform deep analysis and reasoning on updated memory
5. **Save Stage**: Save updated Memory object and session records

**Update Example:**
- **Input**: Existing Memory + new conversation content
- **Processing**: Analyze and update profile and event memory through Pipeline
- **Output**: Updated Memory object + Pipeline execution results

## 3. Database Storage Design

### 3.1 Storage Architecture

Memory objects are persistently stored in a database using a unified Memory table design that supports efficient querying and update operations.

```
Database Layer
├── Memory Unified Table (memories) - Stores complete Memory objects
├── Memory Content Table (memory_contents) - Stores profile and event content
├── Conversation Table (conversations)
├── Conversation Messages Table (conversation_messages)
├── Pipeline Execution Log Table (pipeline_logs)
└── Embedding Vector Table (embedding_vectors) - For semantic search
```

### 3.2 Core Data Table Design

#### 3.2.1 memories (Unified Memory Table)
```sql
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1,
    profile_content TEXT,
    event_content JSON,  -- Array of event paragraphs
    tom_content JSON,    -- Array of ToM insights
    tom_metadata JSON,   -- ToM confidence scores and analysis metadata
    INDEX idx_agent_id (agent_id),
    INDEX idx_updated_at (updated_at)
);
```

#### 3.2.2 conversations (Conversation Table)
```sql
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    conversation_data JSON,  -- Complete conversation content
    pipeline_result JSON,   -- Pipeline execution results
    memory_id UUID,         -- Associated memory ID
    FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
    INDEX idx_agent_id (agent_id),
    INDEX idx_created_at (created_at)
);
```

#### 3.2.3 pipeline_logs (Pipeline Execution Logs)
```sql
CREATE TABLE pipeline_logs (
    log_id UUID PRIMARY KEY,
    memory_id UUID,
    stage_name VARCHAR(50),  -- modification, update, tom
    execution_time TIMESTAMP,
    input_data JSON,
    output_data JSON,
    llm_model VARCHAR(100),
    success BOOLEAN,
    error_message TEXT,
    FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
    INDEX idx_memory_id (memory_id),
    INDEX idx_execution_time (execution_time)
);
```

### 3.3 MemoryRepository Interface

The `MemoryRepository` class provides database operation interfaces:

```python
class MemoryRepository:
    def save_memory(self, memory: Memory) -> bool
    def load_memory_by_agent(self, agent_id: str) -> Optional[Memory]
    def load_memory_by_id(self, memory_id: str) -> Optional[Memory]
    def update_memory(self, memory: Memory) -> bool
    def delete_memory(self, memory_id: str) -> bool
    def search_memories(self, query: str, agent_id: str = None) -> List[Memory]
    def get_memory_history(self, agent_id: str, limit: int = 10) -> List[Memory]
```

## 4. LLM Integration Architecture

### 4.1 LLM Manager Design

The `LLMManager` class provides unified management of multiple LLM providers:

```python
class LLMManager:
    def __init__(self):
        self.providers = {}
        self.current_provider = None
    
    def add_provider(self, name: str, provider: BaseLLM)
    def switch_provider(self, name: str) -> bool
    def get_current_provider() -> BaseLLM
    def list_providers() -> List[str]
```

### 4.2 Supported LLM Providers

- **OpenAI**: GPT-3.5, GPT-4 series
- **Anthropic**: Claude series
- **Google**: Gemini series
- **Azure OpenAI**: Azure-hosted OpenAI models
- **Cohere**: Command series
- **AWS Bedrock**: Multiple models through AWS
- **Together AI**: Open source models
- **Replicate**: Community models
- **Local LLMs**: Self-hosted models

### 4.3 BaseLLM Interface

All LLM providers implement the `BaseLLM` interface:

```python
class BaseLLM:
    def generate(self, prompt: str, **kwargs) -> LLMResponse
    def chat_completion(self, messages: List[Dict], **kwargs) -> LLMResponse
    def get_embeddings(self, texts: List[str]) -> List[List[float]]
```

## 5. Search System Architecture

### 5.1 Search Strategy

The search system uses a hybrid approach combining:
- **Keyword Search**: Traditional text matching
- **Semantic Search**: Embedding-based similarity
- **LLM-Enhanced Search**: Intelligent relevance scoring

### 5.2 Search Components

```python
class SearchEngine:
    def need_search(self, conversation: str) -> bool
    def deep_search(self, query: str, agent_id: str) -> SearchResult
    def semantic_search(self, query: str, embeddings: List) -> List[ScoredResult]
    def rank_results(self, results: List, context: str) -> List[RankedResult]
```

## 6. Error Handling and Monitoring

### 6.1 Error Handling Strategy

- **Graceful Degradation**: System continues functioning with reduced capabilities
- **Retry Mechanisms**: Automatic retry for transient failures
- **Fallback Strategies**: Simple extraction when LLM fails
- **Error Logging**: Comprehensive error tracking

### 6.2 Monitoring and Observability

- **Performance Metrics**: Response times, success rates
- **Memory Usage**: Memory size, update frequency
- **LLM Usage**: Token consumption, model performance
- **Pipeline Monitoring**: Stage-by-stage execution tracking

## 7. Security and Privacy

### 7.1 Data Protection

- **Encryption**: At-rest and in-transit encryption
- **Access Control**: Agent-level isolation
- **Data Anonymization**: PII detection and handling
- **Audit Logging**: Complete operation audit trail

### 7.2 Privacy Compliance

- **GDPR Compliance**: Right to deletion, data portability
- **Data Retention**: Configurable retention policies
- **Consent Management**: User consent tracking
- **Data Minimization**: Store only necessary information

## 8. Scalability and Performance

### 8.1 Scalability Design

- **Horizontal Scaling**: Support for multiple database instances
- **Caching**: Multi-level caching strategy
- **Asynchronous Processing**: Non-blocking operations
- **Load Balancing**: Distribute across multiple LLM providers

### 8.2 Performance Optimization

- **Batch Processing**: Group operations for efficiency
- **Connection Pooling**: Efficient database connections
- **Memory Management**: Optimal memory usage patterns
- **Query Optimization**: Efficient database queries

This architecture provides a robust, scalable, and maintainable foundation for AI memory management with comprehensive LLM integration and advanced psychological modeling capabilities. 