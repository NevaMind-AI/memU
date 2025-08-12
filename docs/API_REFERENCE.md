# MemU API Reference

## 📋 Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Python SDK](#python-sdk)
  - [Installation](#python-installation)
  - [Quick Start](#python-quick-start)
  - [Client Configuration](#client-configuration)
  - [API Methods](#api-methods)
- [JavaScript SDK](#javascript-sdk)
  - [Installation](#javascript-installation)
  - [Quick Start](#javascript-quick-start)
  - [TypeScript Support](#typescript-support)
  - [API Methods](#javascript-api-methods)
- [Data Models](#data-models)
- [Error Codes](#error-codes)
- [Rate Limits](#rate-limits)

## 🌟 Overview

MemU provides RESTful APIs for managing AI companion memories. This document covers both Python and JavaScript SDKs for easy integration.

### Core Features
- **Memorize Conversations**: Store and process conversation data
- **Retrieve Memories**: Search and fetch relevant memories
- **Category Management**: Organize memories by categories
- **Asynchronous Processing**: Track task status for long-running operations

## 🔐 Authentication

All API requests require authentication using an API key. Get your API key from the [MemU Dashboard](https://app-preview.memu.so/api-key/).

### Environment Variables
```bash
export MEMU_API_KEY="your_api_key_here"
export MEMU_API_BASE_URL="https://api-preview.memu.so"  # Optional, defaults to localhost
```

---

## 🐍 Python SDK

### Python Installation

```bash
pip install memu-py
```

### Python Quick Start

```python
import os
from memu import MemuClient

# Initialize client
client = MemuClient(
    base_url="https://api-preview.memu.so",
    api_key=os.getenv("MEMU_API_KEY")
)

# Memorize a conversation
response = client.memorize_conversation(
    conversation="User: Hello! Agent: Hi there, how can I help you today?",
    user_id="user123",
    user_name="John Doe",
    agent_id="agent456",
    agent_name="Assistant"
)

print(f"Task ID: {response.task_id}")
```

### Client Configuration

```python
from memu import MemuClient

client = MemuClient(
    base_url="https://api-preview.memu.so",  # API base URL
    api_key="your_api_key",                  # API key for authentication
    timeout=30.0,                            # Request timeout in seconds
    max_retries=3                            # Maximum retry attempts
)
```

### API Methods

#### `memorize_conversation()`

Stores conversation data for processing by the memory agent.

**Parameters:**
- `conversation` (str | list): Conversation content (string or structured messages)
- `user_id` (str): Unique user identifier
- `user_name` (str): User display name
- `agent_id` (str): Unique agent identifier
- `agent_name` (str): Agent display name
- `session_date` (str, optional): ISO 8601 formatted date

**Returns:** `MemorizeResponse`

```python
# String format
response = client.memorize_conversation(
    conversation="User: What's the weather? Agent: It's sunny today!",
    user_id="user123",
    user_name="Alice",
    agent_id="weather_bot",
    agent_name="Weather Assistant"
)

# Structured format
conversation_messages = [
    {"role": "user", "content": "What's the weather?"},
    {"role": "agent", "content": "It's sunny today!"}
]

response = client.memorize_conversation(
    conversation=conversation_messages,
    user_id="user123",
    user_name="Alice",
    agent_id="weather_bot",
    agent_name="Weather Assistant"
)
```

#### `get_task_status()`

Retrieves the status of a memorization task.

**Parameters:**
- `task_id` (str): Task ID returned from `memorize_conversation()`

**Returns:** `MemorizeTaskStatusResponse`

```python
status = client.get_task_status("task_123456")
print(f"Status: {status.status}")  # PENDING, SUCCESS, or FAILURE
```

#### `retrieve_default_categories()`

Retrieves available memory categories for a user.

**Parameters:**
- `user_id` (str): User identifier
- `agent_id` (str, optional): Filter by specific agent
- `include_inactive` (bool): Include inactive categories (default: False)

**Returns:** `DefaultCategoriesResponse`

```python
categories = client.retrieve_default_categories(
    user_id="user123",
    agent_id="agent456",
    include_inactive=False
)

for category in categories.categories:
    print(f"Category: {category.name}")
    print(f"Memories: {category.memory_count}")
```

#### `retrieve_related_memory_items()`

Searches for memories related to a query.

**Parameters:**
- `user_id` (str): User identifier
- `query` (str): Search query
- `agent_id` (str, optional): Filter by specific agent
- `top_k` (int): Number of results to return (default: 10)
- `min_similarity` (float): Minimum similarity threshold (default: 0.3)
- `include_categories` (list[str], optional): Filter by categories

**Returns:** `RelatedMemoryItemsResponse`

```python
memories = client.retrieve_related_memory_items(
    user_id="user123",
    query="weather conversations",
    top_k=5,
    min_similarity=0.5,
    include_categories=["weather", "general"]
)

for memory in memories.related_memories:
    print(f"Content: {memory.memory.content}")
    print(f"Similarity: {memory.similarity_score}")
```

#### `retrieve_related_clustered_categories()`

Retrieves categories clustered by similarity to a query.

**Parameters:**
- `user_id` (str): User identifier
- `category_query` (str): Category search query
- `agent_id` (str, optional): Filter by specific agent
- `top_k` (int): Number of categories to return (default: 5)
- `min_similarity` (float): Minimum similarity threshold (default: 0.3)

**Returns:** `RelatedClusteredCategoriesResponse`

```python
categories = client.retrieve_related_clustered_categories(
    user_id="user123",
    category_query="personal preferences",
    top_k=3,
    min_similarity=0.4
)

for category in categories.clustered_categories:
    print(f"Category: {category.name}")
    print(f"Similarity: {category.similarity_score}")
```

---

## 🟨 JavaScript SDK

### JavaScript Installation

```bash
npm install memu-js
# or
yarn add memu-js
```

### JavaScript Quick Start

```javascript
import { MemuClient } from 'memu-js';

// Initialize client
const client = new MemuClient({
  baseUrl: 'https://api-preview.memu.so',
  apiKey: process.env.MEMU_API_KEY
});

// Memorize a conversation
const response = await client.memorizeConversation(
  "User: Hello! Agent: Hi there, how can I help you today?",
  "user123",
  "John Doe",
  "agent456",
  "Assistant"
);

console.log(`Task ID: ${response.taskId}`);
```

### TypeScript Support

```typescript
import { MemuClient, MemorizeResponse } from 'memu-js';

const client = new MemuClient({
  baseUrl: 'https://api-preview.memu.so',
  apiKey: process.env.MEMU_API_KEY,
  timeout: 30000,
  maxRetries: 3
});

const response: MemorizeResponse = await client.memorizeConversation(
  "Hello world",
  "user123", 
  "John",
  "agent456",
  "Assistant"
);
```

### JavaScript API Methods

#### `memorizeConversation()`

```typescript
async memorizeConversation(
  conversation: string | Array<{role: string, content: string}>,
  userId: string,
  userName: string,
  agentId: string,
  agentName: string,
  sessionDate?: string
): Promise<MemorizeResponse>
```

**Example:**

```javascript
// String format
const response = await client.memorizeConversation(
  "User: How's the weather? Agent: It's sunny!",
  "user123",
  "Alice",
  "weather_bot", 
  "Weather Assistant"
);

// Structured format
const messages = [
  { role: "user", content: "How's the weather?" },
  { role: "agent", content: "It's sunny!" }
];

const response = await client.memorizeConversation(
  messages,
  "user123",
  "Alice",
  "weather_bot",
  "Weather Assistant"
);
```

#### `getTaskStatus()`

```typescript
async getTaskStatus(taskId: string): Promise<MemorizeTaskStatusResponse>
```

**Example:**

```javascript
const status = await client.getTaskStatus("task_123456");
console.log(`Status: ${status.status}`);
```

#### `retrieveDefaultCategories()`

```typescript
async retrieveDefaultCategories(options: {
  userId: string;
  agentId?: string;
  includeInactive?: boolean;
}): Promise<DefaultCategoriesResponse>
```

**Example:**

```javascript
const categories = await client.retrieveDefaultCategories({
  userId: "user123",
  agentId: "agent456",
  includeInactive: false
});

categories.categories.forEach(category => {
  console.log(`Category: ${category.categoryName}`);
  console.log(`Memories: ${category.memoryCount}`);
});
```

#### `retrieveRelatedMemoryItems()`

```typescript
async retrieveRelatedMemoryItems(options: {
  userId: string;
  agentId?: string;
  query: string;
  topK?: number;
  minSimilarity?: number;
  includeCategories?: string[];
}): Promise<RelatedMemoryItemsResponse>
```

**Example:**

```javascript
const memories = await client.retrieveRelatedMemoryItems({
  userId: "user123",
  query: "weather conversations",
  topK: 5,
  minSimilarity: 0.5,
  includeCategories: ["weather", "general"]
});

memories.relatedMemories.forEach(memory => {
  console.log(`Content: ${memory.memory.content}`);
  console.log(`Similarity: ${memory.similarityScore}`);
});
```

#### `retrieveRelatedClusteredCategories()`

```typescript
async retrieveRelatedClusteredCategories(options: {
  userId: string;
  agentId?: string;
  categoryQuery: string;
  topK?: number;
  minSimilarity?: number;
}): Promise<RelatedClusteredCategoriesResponse>
```

**Example:**

```javascript
const categories = await client.retrieveRelatedClusteredCategories({
  userId: "user123",
  categoryQuery: "personal preferences",
  topK: 3,
  minSimilarity: 0.4
});

categories.clusteredCategories.forEach(category => {
  console.log(`Category: ${category.categoryName}`);
  console.log(`Similarity: ${category.similarityScore}`);
});
```

---

## 📊 Data Models

### MemorizeResponse
```typescript
{
  taskId: string;      // Unique task identifier
  status: string;      // Task status (PENDING, SUCCESS, FAILURE)
  message: string;     // Response message
}
```

### MemorizeTaskStatusResponse
```typescript
{
  taskId: string;      // Task identifier
  status: string;      // Current task status
}
```

### MemoryItem
```typescript
{
  memoryId: string;    // Unique memory identifier
  category: string;    // Memory category
  content: string;     // Memory content
  createdAt: Date;     // Creation timestamp
  updatedAt: Date;     // Last update timestamp
}
```

### CategoryResponse
```typescript
{
  categoryName: string;        // Category name
  categoryType: string;        // Category type
  categoryDescription: string; // Category description
  isActive: boolean;          // Whether category is active
  memories: MemoryItem[];     // Memories in category
  memoryCount: number;        // Number of memories
}
```

### RelatedMemory
```typescript
{
  memory: MemoryItem;          // Memory item
  similarityScore: number;     // Similarity score (0-1)
}
```

### ClusteredCategory
```typescript
{
  categoryName: string;        // Category name
  similarityScore: number;     // Similarity score (0-1)
  memories: MemoryItem[];      // Memories in category
  memoryCount: number;         // Number of memories
}
```

---

## ⚠️ Error Codes

| Code | Exception | Description |
|------|-----------|-------------|
| 401  | MemuAuthenticationException | Invalid or missing API key |
| 403  | MemuAuthenticationException | Insufficient permissions |
| 422  | MemuValidationException | Request validation failed |
| 500+ | MemuAPIException | Server error |
| N/A  | MemuConnectionException | Network/connection error |

---


## 🆘 Support

- **Documentation**: [https://memu.pro/docs](https://memu.pro/docs)
- **Discord Community**: [https://discord.gg/memu](https://discord.gg/memu)
- **Email Support**: [contact@nevamind.ai](mailto:contact@nevamind.ai)
- **GitHub Issues**: [https://github.com/nevamind-ai/memu/issues](https://github.com/nevamind-ai/memu/issues)