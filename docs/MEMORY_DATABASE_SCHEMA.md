# MemU Memory Database Schema Documentation

## Overview

MemU uses PostgreSQL with pgvector extension for memory storage and semantic search capabilities. The database is designed to efficiently store and retrieve character memories, conversation data, and provide full audit trail capabilities through a simple three-table architecture.

## Database Requirements

- **PostgreSQL**: Version 12+ recommended
- **pgvector Extension**: Required for vector operations and semantic search
- **JSONB Support**: For flexible schema storage

## Core Architecture

The MemU system uses a streamlined three-table approach:

1. **`memories`**: Unified table storing all memory content with embeddings and categorization
2. **`memory_history`**: Audit trail table for tracking all memory changes and operations
3. **`conversations`**: Conversation metadata and session management

### Specialized Agent Architecture

The system supports multiple specialized agents, each managing their own memory type through category field:

- **ActivityAgent** → `activity` category (activity summaries from conversations)
- **ProfileAgent** → `profile` category (character profile information)
- **EventAgent** → `event` category (character event records)
- **ReminderAgent** → `reminder` category (important reminders and todo items)
- **InterestAgent** → `interests` category (hobbies and preferences)
- **StudyAgent** → `study` category (learning goals and educational content)
- **Custom Agents** → Custom categories as defined by developers

## Table Schema

### `memories` Table

Unified table that stores all memory content with embeddings and categorization. This simplified design combines metadata and content in a single table for better performance and easier management.

```sql
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    category TEXT,
    content TEXT,
    embedding vector(1536),  -- Default OpenAI embedding dimension
    links JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    happened_at TIMESTAMP
);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT | Primary key, unique identifier for each memory entry |
| `agent_id` | TEXT | Identifier for the AI agent/character |
| `user_id` | TEXT | Identifier for the user |
| `category` | TEXT | Category classification for organizing memories (e.g., 'profile', 'event', 'activity', 'reminder', 'interests', 'study') |
| `content` | TEXT | The actual memory content in text format |
| `embedding` | vector(1536) | Vector embedding for semantic search |
| `links` | JSONB | Related links or references in JSON format |
| `created_at` | TIMESTAMP | When the memory was first created |
| `updated_at` | TIMESTAMP | Last modification timestamp |
| `happened_at` | TIMESTAMP | When the event described in the memory actually happened |

### `memory_history` Table

Audit trail table that tracks all changes and operations performed on memories. This provides complete history tracking for debugging, rollback capabilities, and audit purposes.

```sql
CREATE TABLE IF NOT EXISTS memory_history (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    section TEXT,
    content TEXT,
    links JSONB
);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT | Primary key, unique identifier for each history entry |
| `memory_id` | TEXT | Reference to the memory that was changed |
| `agent_id` | TEXT | Identifier for the AI agent/character |
| `user_id` | TEXT | Identifier for the user |
| `action` | TEXT | Type of action performed (e.g., 'CREATE', 'UPDATE', 'DELETE', 'SEARCH', 'READ') |
| `timestamp` | TIMESTAMP | When the action was performed |
| `section` | TEXT | Specific section or field that was modified (e.g., 'content', 'links', 'category') |
| `content` | TEXT | The content involved in the action (new content for updates, old content for deletes) |
| `links` | JSONB | Links data involved in the action |

### `conversations` Table

Conversation metadata and session management for tracking user interactions and linking them to memory operations.

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    status TEXT DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT | Primary key, unique identifier for each conversation |
| `agent_id` | TEXT | Identifier for the AI agent/character involved |
| `user_id` | TEXT | Identifier for the user |
| `title` | TEXT | Human-readable title or subject of the conversation |
| `summary` | TEXT | Summary of the conversation content |
| `status` | TEXT | Conversation status ('active', 'completed', 'archived') |
| `metadata` | JSONB | Additional conversation metadata (context, settings, etc.) |
| `created_at` | TIMESTAMP | When the conversation was started |
| `updated_at` | TIMESTAMP | Last modification timestamp |
| `ended_at` | TIMESTAMP | When the conversation was ended or completed |

#### Supported Action Types

| Action | Description | When Used |
|--------|-------------|-----------|
| `CREATE` | New memory was created | When inserting new memory records |
| `UPDATE` | Existing memory was modified | When updating memory content, links, or metadata |
| `DELETE` | Memory was removed | When deleting memory records |
| `READ` | Memory was accessed | When retrieving memory content (optional logging) |
| `SEARCH` | Memory was found via search | When memory appears in search results (optional logging) |
| `EMBED` | Embedding was generated/updated | When vector embeddings are created or updated |

#### Section Examples

The `section` field indicates what part of the memory was affected:

| Section | Description | Use Cases |
|---------|-------------|-----------|
| `content` | Main content text was changed | Content updates, corrections |
| `links` | Links/references were modified | Adding/removing references |
| `category` | Category was changed | Reclassifying memories |
| `embedding` | Vector embedding was updated | Embedding regeneration |
| `metadata` | Timestamps or other metadata changed | System updates |
| `full` | Entire memory record affected | Creation, deletion, or complete replacement |

#### Supported Memory Categories

The system supports flexible memory categories managed by specialized agents:

| Memory Category | Description | Managed By |
|-----------------|-------------|------------|
| `activity` | Activity summaries from conversations | ActivityAgent |
| `profile` | Character profile information | ProfileAgent |
| `event` | Character event records | EventAgent |
| `reminder` | Important reminders and todo items | ReminderAgent |
| `interests` | Hobbies, interests, and preferences | InterestAgent |
| `study` | Learning goals, courses, and educational content | StudyAgent |
| **Custom Categories** | Developers can define additional memory categories | Custom Agents |

#### Category Examples

The `category` field provides organization and classification of memories:

| Category | Description | Use Cases |
|----------|-------------|-----------|
| `profile` | Character profile information | Personal details, characteristics |
| `event` | Character event records | Important life events, activities |
| `activity` | Activity summaries | Daily activities, routine behaviors |
| `reminder` | Important reminders | Tasks, appointments, important notes |
| `interests` | Hobbies and preferences | Likes, dislikes, hobby activities |
| `study` | Learning and education | Courses, skills, knowledge |
| **Custom** | User or agent-defined categories | Domain-specific classifications |

#### Conversation Status Types

| Status | Description | When Used |
|--------|-------------|-----------|
| `active` | Conversation is ongoing | Default status for new conversations |
| `completed` | Conversation finished normally | When user explicitly ends conversation |
| `archived` | Conversation archived for reference | Long-term storage of inactive conversations |
| `paused` | Conversation temporarily suspended | When conversation is on hold |

#### Links Field

The `links` field stores related references in JSONB format:

```json
{
  "urls": ["https://example.com/article"],
  "files": ["/path/to/document.pdf"],
  "related_memories": ["memory_id_1", "memory_id_2"],
  "external_refs": ["conversation_id", "message_id"]
}
```

#### Metadata Examples

The `metadata` field in conversations can store various contextual information:

```json
{
  "language": "en",
  "platform": "web",
  "client_version": "1.0.0",
  "memory_context": ["profile", "recent_events"],
  "conversation_type": "general",
  "user_preferences": {
    "response_length": "medium",
    "formality": "casual"
  }
}
```

#### Constraints

**memories Table:**
- **Primary Key**: `id`
- **NOT NULL**: `agent_id`, `user_id` must be provided

**memory_history Table:**
- **Primary Key**: `id`
- **NOT NULL**: `memory_id`, `agent_id`, `user_id`, `action`, `timestamp` must be provided
- **Foreign Key**: `memory_id` references memories(id) (soft reference, allows history of deleted memories)

**conversations Table:**
- **Primary Key**: `id`
- **NOT NULL**: `agent_id`, `user_id` must be provided
- **Default Values**: `status` defaults to 'active'

## Database Indexes

The three-table structure includes comprehensive indexes for optimal query performance:

### Primary Indexes

```sql
-- Indexes for memories table
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_agent_user ON memories(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at);
CREATE INDEX IF NOT EXISTS idx_memories_happened_at ON memories(happened_at);

-- Vector similarity search index using HNSW
CREATE INDEX IF NOT EXISTS idx_memories_vector_hnsw
    ON memories USING hnsw (embedding vector_cosine_ops);

-- JSONB indexes for links
CREATE INDEX IF NOT EXISTS idx_memories_links_gin ON memories USING gin (links);

-- Composite indexes for advanced query patterns
CREATE INDEX IF NOT EXISTS idx_memories_agent_user_category
    ON memories (agent_id, user_id, category);

CREATE INDEX IF NOT EXISTS idx_memories_category_happened
    ON memories (category, happened_at);

CREATE INDEX IF NOT EXISTS idx_memories_embedding_filtered
    ON memories (category) 
    WHERE embedding IS NOT NULL;

-- Indexes for memory_history table
CREATE INDEX IF NOT EXISTS idx_memory_history_memory_id ON memory_history(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_history_agent_id ON memory_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_memory_history_user_id ON memory_history(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_history_action ON memory_history(action);
CREATE INDEX IF NOT EXISTS idx_memory_history_timestamp ON memory_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_memory_history_section ON memory_history(section);

-- JSONB indexes for history links
CREATE INDEX IF NOT EXISTS idx_memory_history_links_gin ON memory_history USING gin (links);

-- Composite indexes for history queries
CREATE INDEX IF NOT EXISTS idx_memory_history_memory_timestamp
    ON memory_history (memory_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_memory_history_agent_user_timestamp
    ON memory_history (agent_id, user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_memory_history_action_timestamp
    ON memory_history (action, timestamp DESC);

-- Indexes for conversations table
CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_agent_user ON conversations(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_conversations_ended_at ON conversations(ended_at);

-- JSONB indexes for conversation metadata
CREATE INDEX IF NOT EXISTS idx_conversations_metadata_gin ON conversations USING gin (metadata);

-- Composite indexes for conversation queries
CREATE INDEX IF NOT EXISTS idx_conversations_agent_user_status
    ON conversations (agent_id, user_id, status);

CREATE INDEX IF NOT EXISTS idx_conversations_status_updated
    ON conversations (status, updated_at DESC);
```

### Index Benefits

| Index | Purpose | Query Pattern |
|-------|---------|---------------|
| **Memories Table** |
| `idx_memories_agent_id` | Fast agent-based queries | `WHERE agent_id = ?` |
| `idx_memories_user_id` | Fast user-based queries | `WHERE user_id = ?` |
| `idx_memories_agent_user` | Fast agent+user queries | `WHERE agent_id = ? AND user_id = ?` |
| `idx_memories_category` | Category-based filtering | `WHERE category = ?` |
| `idx_memories_created_at` | Created time queries | `ORDER BY created_at`, time-range queries |
| `idx_memories_updated_at` | Updated time queries | `ORDER BY updated_at`, time-range queries |
| `idx_memories_happened_at` | Event time queries | `ORDER BY happened_at`, time-range queries |
| `idx_memories_vector_hnsw` | Semantic similarity search | Vector cosine similarity queries |
| `idx_memories_links_gin` | JSONB link searches | Links field searches |
| `idx_memories_agent_user_category` | Exact memory lookup | `WHERE agent_id = ? AND user_id = ? AND category = ?` |
| `idx_memories_category_happened` | Category+time combinations | `WHERE category = ? ORDER BY happened_at` |
| `idx_memories_embedding_filtered` | Optimized vector queries | Search only memories with embeddings |
| **History Table** |
| `idx_memory_history_memory_id` | History for specific memory | `WHERE memory_id = ?` |
| `idx_memory_history_agent_id` | Agent history queries | `WHERE agent_id = ?` |
| `idx_memory_history_action` | Action-based filtering | `WHERE action = ?` |
| `idx_memory_history_timestamp` | Temporal history queries | `ORDER BY timestamp`, time-range queries |
| `idx_memory_history_memory_timestamp` | Memory timeline | `WHERE memory_id = ? ORDER BY timestamp` |
| `idx_memory_history_agent_user_timestamp` | User activity timeline | `WHERE agent_id = ? AND user_id = ? ORDER BY timestamp` |
| **Conversations Table** |
| `idx_conversations_agent_id` | Agent conversation queries | `WHERE agent_id = ?` |
| `idx_conversations_user_id` | User conversation queries | `WHERE user_id = ?` |
| `idx_conversations_status` | Status-based filtering | `WHERE status = ?` |
| `idx_conversations_created_at` | Creation time queries | `ORDER BY created_at` |
| `idx_conversations_agent_user_status` | Active conversations lookup | `WHERE agent_id = ? AND user_id = ? AND status = ?` |

## Architecture Benefits

The streamlined three-table design provides several advantages:

### 🚀 Performance Benefits
- **Simplified Queries**: Minimal JOIN operations needed
- **Better Caching**: Three focused tables fit well in database buffer pools
- **Faster Inserts**: Direct operations without complex relationships
- **Optimized Indexes**: Direct indexing on all searchable fields
- **Efficient History**: Separate history table doesn't impact main queries

### 🔧 Operational Benefits
- **Complete Audit Trail**: Full history of all memory operations
- **Conversation Tracking**: Centralized conversation management
- **Rollback Capability**: Can restore previous memory states
- **Debugging Support**: Trace all changes for troubleshooting
- **Compliance**: Audit requirements for sensitive applications
- **Simple Backup/Restore**: Three well-defined tables to manage

### 📈 Scalability Benefits
- **Horizontal Partitioning**: Can partition all tables by agent_id or user_id
- **History Archiving**: Old history records can be archived separately
- **Conversation Archiving**: Completed conversations can be moved to cold storage
- **Reduced Lock Contention**: History writes don't block memory reads
- **Better Compression**: Related data stored together
- **Efficient Replication**: Clear table separation for replication strategies

### 🎯 Simplicity Benefits
- **Minimal Schema**: Only three tables to understand and maintain
- **Clear Separation**: Each table has a distinct, focused purpose
- **Easy Migration**: Simple schema evolution and data migration
- **Developer Friendly**: Intuitive table relationships and queries
- **Reduced Complexity**: No complex foreign key constraints or cascading operations

## Future Enhancements

### Planned Features
- **Memory Rollback**: API to restore memories to previous states using history
- **Change Analytics**: Statistics on memory modification patterns
- **Conversation Analytics**: Insights into conversation patterns and effectiveness
- **Advanced Search**: Cross-table search combining memories and conversations
- **Automated Archiving**: Policy-based archiving of old conversations and history
- **Performance Monitoring**: Built-in metrics for query performance optimization
