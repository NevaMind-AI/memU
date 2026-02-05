# 🔥🔥🔥 MAD COMBO OPTIONS FOR MEMU HACKATHON 🔥🔥🔥

> **Goal:** Implement high-impact features that MemU is missing, sourced from competitor analysis of 7 memory repos (memoripy, memlayer, ReMe, memX, memphora-sdk, MemOS, memor).

---

## 📋 COMPLETE FEATURE GAP ANALYSIS

### FEATURES MEMU IS MISSING (Deep Scan Results)

#### FROM MEMORIPY:
- ❌ `access_counts[]` - Track how often each memory is accessed
- ❌ `timestamps[]` - Track when memory was created/last accessed
- ❌ `decay_factor` - Exponential time-based decay: `np.exp(-decay_rate * time_diff)`
- ❌ `reinforcement_factor` - Log-scaled access boost: `np.log1p(access_count)`
- ❌ `adjusted_similarity` - `similarity * decay_factor * reinforcement_factor`
- ❌ Short-term → Long-term memory promotion (when `access_count > 10`)
- ❌ `nx.Graph()` concept associations (NetworkX graph)
- ❌ `spreading_activation()` - Spread activation through concept graph
- ❌ `cluster_interactions()` - KMeans clustering for hierarchical memory
- ❌ `semantic_memory` clusters - Retrieve from semantic memory clusters

#### FROM MEMLAYER:
- ❌ `SalienceGate` - Filter what's worth saving vs noise
- ❌ `SalienceMode.LOCAL` - Local ML model for salience
- ❌ `SalienceMode.ONLINE` - OpenAI API for salience
- ❌ `SalienceMode.LIGHTWEIGHT` - Keyword-based salience (no embeddings)
- ❌ `SALIENT_PROTOTYPES` / `NON_SALIENT_PROTOTYPES` - Prototype sentences
- ❌ `is_worth_saving()` - Determine if text should be saved
- ❌ `CurationService` - Background memory decay/expiration
- ❌ `_calculate_relevance()` - Score based on age, recency, attention
- ❌ Auto-archive low-relevance memories
- ❌ Auto-delete expired memories (`expiration_timestamp`)
- ❌ `SchedulerService` - Background task scheduler
- ❌ `get_due_tasks_for_user()` - Check for pending scheduled tasks
- ❌ `ConsolidationService` - Background knowledge extraction
- ❌ `analyze_and_extract_knowledge()` - Extract facts, entities, relationships
- ❌ `NetworkXStorage` - Graph storage for entities/relationships
- ❌ `add_entity()` / `add_relationship()` - Knowledge graph operations
- ❌ `get_subgraph_context()` - Graph traversal for context
- ❌ `find_matching_nodes()` - Fuzzy entity matching
- ❌ `_find_canonical_entity()` - Entity deduplication
- ❌ `_merge_entity_nodes()` - Merge duplicate entities
- ❌ `importance_score` / `expiration_timestamp` metadata
- ❌ `track_memory_access()` - Track when memories are accessed
- ❌ Task reminders system (`add_task`, `get_pending_tasks`, `update_task_status`)

#### FROM REME:
- ❌ `UpdateMemoryFreqOp` - Increment frequency counter on recall
- ❌ `metadata["freq"]` - Frequency counter in metadata
- ❌ `UpdateMemoryUtilityOp` - Increment utility score when useful
- ❌ `metadata["utility"]` - Utility score in metadata
- ❌ `DeleteMemoryOp` - Delete based on freq/utility thresholds
- ❌ `utility/freq < threshold` pruning - Prune low-value memories
- ❌ **MEMORY TYPES:**
  - ❌ `TaskMemory` - Task-related information
  - ❌ `PersonalMemory` - Personal info with `target` and `reflection_subject`
  - ❌ `ToolMemory` - Tool call execution history
  - ❌ `ToolCallResult` - Record tool execution results with hash deduplication
- ❌ `MemoryDeduplicationOp` - Remove duplicate memories using embedding similarity
- ❌ `WorkingMemory` operations:
  - ❌ `MessageCompressOp` - LLM-based compression for long conversations
  - ❌ `MessageCompactOp` - Compact verbose tool messages
  - ❌ `MessageOffloadOp` - Orchestrate compaction + compression
  - ❌ `WorkingSummaryMode.COMPACT/COMPRESS/AUTO`
- ❌ `UpdateMemory` tool - Update/edit existing memories
- ❌ `session_memory_id` tracking - Track memories per session
- ❌ Tool memory statistics (`avg_token_cost`, `success_rate`, `avg_time_cost`, `avg_score`)

#### FROM MEMX:
- ❌ `pubsub.py` - Real-time pub/sub system
- ❌ `subscribe(key, websocket)` - WebSocket subscriptions
- ❌ `publish(key, payload)` - Broadcast updates to subscribers
- ❌ `set_value()` with timestamps - Last-write-wins with timestamps
- ❌ Redis-backed shared memory - Multi-agent shared state
- ❌ `register_schema()` / `validate_schema()` - JSON schema validation

#### FROM MEMOS (MemOS):
- ❌ **Memory Scheduler System:**
  - ❌ `BaseScheduler` - Full task scheduling infrastructure
  - ❌ `SchedulerDispatcher` - Parallel task dispatch
  - ❌ `ScheduleTaskQueue` - Priority task queue
  - ❌ `TaskStatusTracker` - Track task status in Redis
  - ❌ `TaskPriorityLevel` - Priority levels for tasks
- ❌ `MemoryMonitorItem` - Monitor memory with importance scores
- ❌ `replace_working_memory()` - Replace working memory after reranking
- ❌ `update_activation_memory()` - Update activation memory periodically
- ❌ `transform_working_memories_to_monitors()` - Convert memories to monitors
- ❌ `visibility` field - Public/private memory visibility
- ❌ `confidence` score - Confidence level for memories
- ❌ `status` field (activated/archived) - Memory activation status
- ❌ `tags` field - Memory tagging system
- ❌ `entities` extraction - Extract entities from memories

#### FROM MEMPHORA-SDK:
- ❌ `store_shared()` - Store shared memory for groups
- ❌ Multi-agent crew memory - Shared memory for agent crews
- ❌ Per-agent namespaces - Isolated memory per agent
- ❌ Framework integrations (AutoGen, CrewAI, LangChain, LlamaIndex)

---

---

## 🏆 COMBO 1: "INTELLIGENT MEMORY LIFECYCLE"

**Theme:** Memory that learns, ages, and self-curates like human memory

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Decay & Reinforcement | memoripy | 3 pts | LOW |
| Frequency & Utility Tracking | ReMe | 3 pts | LOW |
| Auto-Pruning Low-Value Memories | ReMe | 3 pts | LOW |

**Total: 9 pts | LOW-MEDIUM effort**

### Why it's MAD:

```
Memory accessed often → gets STRONGER (reinforcement)
Memory ignored → gets WEAKER (decay)
Memory with low utility/freq ratio → gets DELETED automatically

Result: Self-healing, self-optimizing memory that mimics human forgetting!
```

### The Pitch:
> "MemU now has HUMAN-LIKE memory - it remembers what matters and forgets what doesn't!"

### Technical Implementation:

```python
# Decay formula (from memoripy)
decay_factor = np.exp(-decay_rate * time_diff)
reinforcement_factor = np.log1p(access_count)
adjusted_similarity = similarity * decay_factor * reinforcement_factor

# Pruning logic (from ReMe)
if freq >= freq_threshold:
    if utility / freq < utility_threshold:
        delete_memory(memory_id)
```

---

## 🏆 COMBO 2: "SMART MEMORY GATE"

**Theme:** Don't save garbage, only save gold

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Salience Filtering | memlayer | 3-5 pts | MEDIUM |
| Decay & Reinforcement | memoripy | 3 pts | LOW |
| Background Curation Service | memlayer | 3 pts | MEDIUM |

**Total: 9-11 pts | MEDIUM effort**

### Why it's MAD:

```
INPUT: "Hello!" → BLOCKED (not salient)
INPUT: "My name is John, I work at Google" → SAVED (salient)
BACKGROUND: Old unused memories → AUTO-ARCHIVED
RETRIEVAL: Frequently accessed → BOOSTED

Result: Clean, high-quality memory that doesn't bloat!
```

### The Pitch:
> "MemU now has a BOUNCER - only important memories get in, garbage stays out!"

### Technical Implementation:

```python
# Salience Gate (from memlayer)
class SalienceGate:
    SALIENT_PROTOTYPES = ["My name is...", "I work at...", "The deadline is..."]
    NON_SALIENT_PROTOTYPES = ["Hello", "Thanks", "Okay", "Got it"]

    def is_worth_saving(self, text: str) -> bool:
        # Compare similarity to salient vs non-salient prototypes
        salient_score = max_similarity(text, SALIENT_PROTOTYPES)
        non_salient_score = max_similarity(text, NON_SALIENT_PROTOTYPES)
        return salient_score > (non_salient_score + threshold)
```

---

## 🏆 COMBO 3: "KNOWLEDGE BRAIN"

**Theme:** Memory that understands relationships

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Knowledge Graph | memlayer | 5 pts | HIGH |
| Entity Extraction | memlayer | 3 pts | MEDIUM |
| Graph Traversal Retrieval | memlayer | 3 pts | MEDIUM |

**Total: 11 pts | HIGH effort**

### Why it's MAD:

```
INPUT: "John works at Google. Sarah is John's wife."

GRAPH:
    John --[works_at]--> Google
    John --[married_to]--> Sarah

QUERY: "Who is related to Google?"
RESULT: John (works there), Sarah (married to John who works there)

Result: Memory that REASONS about relationships!
```

### The Pitch:
> "MemU now has a BRAIN - it understands how things connect!"

### Technical Implementation:

```python
# Knowledge Graph (from memlayer)
import networkx as nx

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.Graph()

    def add_entity(self, name: str, node_type: str):
        self.graph.add_node(name, type=node_type)

    def add_relationship(self, subject: str, predicate: str, obj: str):
        self.graph.add_edge(subject, obj, relation=predicate)

    def get_subgraph_context(self, entity: str, depth: int = 2):
        # Traverse graph for related entities
        return nx.ego_graph(self.graph, entity, radius=depth)
```

---

## 🏆 COMBO 4: "MEMORY EVOLUTION" ⭐ TOP PICK

**Theme:** Memory that evolves and improves itself

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Salience Gate (LIGHTWEIGHT mode) | memlayer | 3 pts | LOW |
| Decay & Reinforcement | memoripy | 3 pts | LOW |
| Frequency & Utility | ReMe | 3 pts | LOW |
| Auto-Pruning | ReMe | 3 pts | LOW |

**Total: 12 pts | LOW-MEDIUM effort**

### Why it's MAD:

```
STAGE 1: Salience Gate filters noise at INPUT
STAGE 2: Decay/Reinforcement adjusts scores at RETRIEVAL
STAGE 3: Frequency/Utility tracks VALUE over time
STAGE 4: Auto-Pruning DELETES low-value memories

Result: FULL LIFECYCLE MANAGEMENT - from birth to death!
```

### The Pitch:
> "MemU memories now have a LIFECYCLE - they're born, they grow, they age, they die!"

### Memory Lifecycle Diagram:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY LIFECYCLE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   INPUT ──► [SALIENCE GATE] ──► SAVE or REJECT                  │
│                    │                                             │
│                    ▼                                             │
│              ┌─────────┐                                         │
│              │ MEMORY  │ ◄── access_count, last_accessed        │
│              │  ITEM   │ ◄── freq, utility, salience_score      │
│              └────┬────┘                                         │
│                   │                                              │
│         ┌────────┴────────┐                                      │
│         ▼                 ▼                                      │
│   [RETRIEVAL]       [BACKGROUND]                                 │
│         │                 │                                      │
│   decay_factor      auto_prune()                                 │
│   reinforcement     if utility/freq < threshold                  │
│         │                 │                                      │
│         ▼                 ▼                                      │
│   BOOSTED SCORE     DELETE MEMORY                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 COMPARISON TABLE

| Combo | Points | Effort | WOW Factor | Complexity | Recommendation |
|-------|--------|--------|------------|------------|----------------|
| 1. Intelligent Lifecycle | 9 | LOW | ⭐⭐⭐⭐ | LOW | ✅ SAFE BET |
| 2. Smart Gate | 9-11 | MEDIUM | ⭐⭐⭐⭐ | MEDIUM | ✅ GOOD |
| 3. Knowledge Brain | 11 | HIGH | ⭐⭐⭐⭐⭐ | HIGH | ⚠️ RISKY |
| 4. Memory Evolution | 12 | LOW-MED | ⭐⭐⭐⭐⭐ | MEDIUM | 🏆 **BEST COMBO** |

---

## 🎯 RECOMMENDATION: COMBO 4 "MEMORY EVOLUTION"

### Why This Combo Wins:

1. **12 points** - highest point potential
2. **LOW-MEDIUM effort** - achievable in hackathon timeframe
3. **4 features that SYNERGIZE** - each builds on the other
4. **UNIQUE story** - "memory lifecycle" is a compelling narrative
5. **Easy to demo** - show memory being filtered, decaying, getting pruned

### Implementation Order:

```
Step 1: Add fields to MemoryItem model
        - access_count: int = 0
        - last_accessed: datetime
        - freq: int = 0
        - utility: int = 0
        - salience_score: float = 0.0

Step 2: Implement lightweight salience gate (keyword-based, no ML)
        - SALIENT_KEYWORDS list
        - NON_SALIENT_KEYWORDS list
        - is_worth_saving() function

Step 3: Implement decay-aware retrieval
        - Modify cosine_topk() to apply decay formula
        - Update access_count and last_accessed on retrieval

Step 4: Implement frequency/utility tracking
        - Increment freq on every retrieval
        - Increment utility when memory contributes to response

Step 5: Implement auto-pruning
        - Background check for low utility/freq ratio
        - Delete memories below threshold
```

### Files to Modify:

```
memU/src/memu/database/models.py          # Add new fields
memU/src/memu/database/inmemory/vector.py # Decay-aware retrieval
memU/src/memu/app/memorize.py             # Salience gate
memU/src/memu/app/retrieve.py             # Frequency/utility tracking
memU/src/memu/app/service.py              # Auto-pruning service
```

---

## 📚 Reference Implementations

### From memoripy (Decay & Reinforcement):
- File: `prospects/memoripy/memoripy/memory_store.py`
- Key functions: `retrieve()`, `classify_memory()`

### From memlayer (Salience Gate):
- File: `prospects/memlayer/memlayer/ml_gate.py`
- Key class: `SalienceGate`

### From ReMe (Frequency & Utility):
- Files:
  - `prospects/ReMe/reme_ai/vector_store/update_memory_freq_op.py`
  - `prospects/ReMe/reme_ai/vector_store/update_memory_utility_op.py`
  - `prospects/ReMe/reme_ai/vector_store/delete_memory_op.py`

---

## 🚀 Ready to Implement?

Choose your combo and let's build! 🔥


## 🏆 UPDATED MAD COMBOS (After Deep Scan)

---

## 🏆 COMBO 1: "INTELLIGENT MEMORY LIFECYCLE"

**Theme:** Memory that learns, ages, and self-curates like human memory

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Decay & Reinforcement | memoripy | 3 pts | LOW |
| Frequency & Utility Tracking | ReMe | 3 pts | LOW |
| Auto-Pruning Low-Value Memories | ReMe | 3 pts | LOW |

**Total: 9 pts | LOW-MEDIUM effort**

### Why it's MAD:

```
Memory accessed often → gets STRONGER (reinforcement)
Memory ignored → gets WEAKER (decay)
Memory with low utility/freq ratio → gets DELETED automatically

Result: Self-healing, self-optimizing memory that mimics human forgetting!
```

### The Pitch:
> "MemU now has HUMAN-LIKE memory - it remembers what matters and forgets what doesn't!"

---

## 🏆 COMBO 2: "SMART MEMORY GATE"

**Theme:** Don't save garbage, only save gold

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Salience Filtering | memlayer | 3-5 pts | MEDIUM |
| Decay & Reinforcement | memoripy | 3 pts | LOW |
| Background Curation Service | memlayer | 3 pts | MEDIUM |

**Total: 9-11 pts | MEDIUM effort**

### Why it's MAD:

```
INPUT: "Hello!" → BLOCKED (not salient)
INPUT: "My name is John, I work at Google" → SAVED (salient)
BACKGROUND: Old unused memories → AUTO-ARCHIVED
RETRIEVAL: Frequently accessed → BOOSTED

Result: Clean, high-quality memory that doesn't bloat!
```

### The Pitch:
> "MemU now has a BOUNCER - only important memories get in, garbage stays out!"

---

## 🏆 COMBO 3: "KNOWLEDGE BRAIN"

**Theme:** Memory that understands relationships

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Knowledge Graph (NetworkX) | memlayer | 5 pts | HIGH |
| Entity Extraction & Deduplication | memlayer | 3 pts | MEDIUM |
| Graph Traversal Retrieval | memlayer | 3 pts | MEDIUM |

**Total: 11 pts | HIGH effort**

### Why it's MAD:

```
INPUT: "John works at Google. Sarah is John's wife."

GRAPH:
    John --[works_at]--> Google
    John --[married_to]--> Sarah

QUERY: "Who is related to Google?"
RESULT: John (works there), Sarah (married to John who works there)

Result: Memory that REASONS about relationships!
```

### The Pitch:
> "MemU now has a BRAIN - it understands how things connect!"

---

## 🏆 COMBO 4: "MEMORY EVOLUTION" ⭐ TOP PICK

**Theme:** Memory that evolves and improves itself

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| Salience Gate (LIGHTWEIGHT mode) | memlayer | 3 pts | LOW |
| Decay & Reinforcement | memoripy | 3 pts | LOW |
| Frequency & Utility | ReMe | 3 pts | LOW |
| Auto-Pruning | ReMe | 3 pts | LOW |

**Total: 12 pts | LOW-MEDIUM effort**

### Why it's MAD:

```
STAGE 1: Salience Gate filters noise at INPUT
STAGE 2: Decay/Reinforcement adjusts scores at RETRIEVAL
STAGE 3: Frequency/Utility tracks VALUE over time
STAGE 4: Auto-Pruning DELETES low-value memories

Result: FULL LIFECYCLE MANAGEMENT - from birth to death!
```

### The Pitch:
> "MemU memories now have a LIFECYCLE - they're born, they grow, they age, they die!"

---

## 🏆 COMBO 5: "MEMORY TYPES" (NEW!)

**Theme:** Different memory types for different purposes

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| TaskMemory type | ReMe | 3 pts | MEDIUM |
| PersonalMemory type | ReMe | 3 pts | MEDIUM |
| ToolMemory type | ReMe | 5 pts | HIGH |
| Memory Deduplication | ReMe | 3 pts | MEDIUM |

**Total: 14 pts | MEDIUM-HIGH effort**

### Why it's MAD:

```
TaskMemory: "Complete the report by Friday"
  - when_to_use: "When user asks about deadlines"
  - content: "Report due Friday"

PersonalMemory: "User prefers dark mode"
  - target: "user_preferences"
  - reflection_subject: "ui_settings"

ToolMemory: "file_reader tool usage history"
  - tool_call_results: [...]
  - statistics: {avg_token_cost, success_rate, avg_score}

Result: Specialized memory for specialized tasks!
```

### The Pitch:
> "MemU now has SPECIALIZED MEMORY - task memory, personal memory, tool memory!"

---

## 🏆 COMBO 6: "WORKING MEMORY COMPRESSION" (NEW!)

**Theme:** Handle long conversations without losing context

| Component | Source | Points | Effort |
|-----------|--------|--------|--------|
| MessageCompressOp | ReMe | 3 pts | MEDIUM |
| MessageCompactOp | ReMe | 3 pts | MEDIUM |
| MessageOffloadOp | ReMe | 3 pts | MEDIUM |

**Total: 9 pts | MEDIUM effort**

### Why it's MAD:

```
LONG CONVERSATION (50k tokens) → COMPRESS → STATE SNAPSHOT (5k tokens)

Modes:
- COMPACT: Store full content externally, keep short previews
- COMPRESS: LLM-based compression to generate dense summaries
- AUTO: Compact first, then compress if needed

Result: Handle infinite conversations without context overflow!
```

### The Pitch:
> "MemU now handles INFINITE conversations - compress, compact, never forget!"

---

## 📊 UPDATED COMPARISON TABLE

| Combo | Points | Effort | WOW Factor | Complexity | Recommendation |
|-------|--------|--------|------------|------------|----------------|
| 1. Intelligent Lifecycle | 9 | LOW | ⭐⭐⭐⭐ | LOW | ✅ SAFE BET |
| 2. Smart Gate | 9-11 | MEDIUM | ⭐⭐⭐⭐ | MEDIUM | ✅ GOOD |
| 3. Knowledge Brain | 11 | HIGH | ⭐⭐⭐⭐⭐ | HIGH | ⚠️ RISKY |
| 4. Memory Evolution | 12 | LOW-MED | ⭐⭐⭐⭐⭐ | MEDIUM | 🏆 **BEST COMBO** |
| 5. Memory Types | 14 | MED-HIGH | ⭐⭐⭐⭐⭐ | HIGH | 🔥 HIGH POINTS |
| 6. Working Memory | 9 | MEDIUM | ⭐⭐⭐⭐ | MEDIUM | ✅ GOOD |

---

## 🎯 FINAL RECOMMENDATION

### For MAX POINTS with REASONABLE EFFORT: **COMBO 4 "MEMORY EVOLUTION"**

**Why?**
1. **12 points** - highest point potential for effort
2. **LOW-MEDIUM effort** - achievable in hackathon timeframe
3. **4 features that SYNERGIZE** - each builds on the other
4. **UNIQUE story** - "memory lifecycle" is a compelling narrative
5. **Easy to demo** - show memory being filtered, decaying, getting pruned

### Implementation Order:

```
Step 1: Add fields to MemoryItem model
        - access_count: int = 0
        - last_accessed: datetime
        - freq: int = 0
        - utility: int = 0
        - salience_score: float = 0.0

Step 2: Implement lightweight salience gate (keyword-based, no ML)
        - SALIENT_KEYWORDS list
        - NON_SALIENT_KEYWORDS list
        - is_worth_saving() function

Step 3: Implement decay-aware retrieval
        - Modify cosine_topk() to apply decay formula
        - Update access_count and last_accessed on retrieval

Step 4: Implement frequency/utility tracking
        - Increment freq on every retrieval
        - Increment utility when memory contributes to response

Step 5: Implement auto-pruning
        - Background check for low utility/freq ratio
        - Delete memories below threshold
```

### Files to Modify:

```
memU/src/memu/database/models.py          # Add new fields
memU/src/memu/database/inmemory/vector.py # Decay-aware retrieval
memU/src/memu/app/memorize.py             # Salience gate
memU/src/memu/app/retrieve.py             # Frequency/utility tracking
memU/src/memu/app/service.py              # Auto-pruning service
```

---

## 📚 Reference Implementations

### From memoripy (Decay & Reinforcement):
- File: `prospects/memoripy/memoripy/memory_store.py`
- Key functions: `retrieve()`, `classify_memory()`

### From memlayer (Salience Gate + Knowledge Graph):
- File: `prospects/memlayer/memlayer/ml_gate.py` - SalienceGate
- File: `prospects/memlayer/memlayer/storage/networkx.py` - Knowledge Graph
- File: `prospects/memlayer/memlayer/services.py` - CurationService

### From ReMe (Frequency & Utility + Memory Types):
- File: `prospects/ReMe/reme_ai/vector_store/update_memory_freq_op.py`
- File: `prospects/ReMe/reme_ai/vector_store/update_memory_utility_op.py`
- File: `prospects/ReMe/reme_ai/vector_store/delete_memory_op.py`
- File: `prospects/ReMe/reme_ai/schema/memory.py` - Memory types
- File: `prospects/ReMe/reme_ai/summary/task/memory_deduplication_op.py`
- File: `prospects/ReMe/reme_ai/summary/working/` - Working memory ops

### From MemOS (Scheduler):
- File: `prospects/MemOS/src/memos/mem_scheduler/base_scheduler.py`

---

## 🚀 Ready to Implement?

Choose your combo and let's build! 🔥
