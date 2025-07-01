<div align="center">
  <img src="assets/logo.png" alt="PersonaLab Logo" width="200" height="200">
  
  # PersonaLab

  🧠 **AI Memory and Conversation Management** - Simple as mem0, Powerful as PersonaLab
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![PyPI version](https://badge.fury.io/py/personalab.svg)](https://badge.fury.io/py/personalab)
</div>

PersonaLab is a comprehensive AI memory and conversation management system that provides intelligent profile management, conversation recording, and advanced semantic search capabilities for AI agents. It combines persistent memory storage, conversation analysis, psychological modeling, and vector-based retrieval for building sophisticated AI applications.

## ⚡ Quick Start

### Installation

```bash
pip install personalab[ai]  # Core AI features with OpenAI support
# or
pip install personalab[all]  # All features
```

### Usage (3 lines of code!)

```python
from personalab import Persona

# Default OpenAI usage (reads OPENAI_API_KEY from .env)
persona = Persona(agent_id="my_ai_assistant")

# Or specify LLM provider explicitly
persona = Persona.create_openai(agent_id="openai_assistant")
persona = Persona.create_anthropic(agent_id="claude_assistant")

def chat_with_memories(message: str) -> str:
    return persona.chat(message)

# That's it! Your AI now has persistent memory and conversation retrieval
print(chat_with_memories("Hi, I'm learning Python"))
print(chat_with_memories("What was I learning?"))  # Remembers previous context
```

### Environment Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and add your API keys
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here

# 3. Test configuration
python setup_env.py
```

---

## 🌟 Key Features

### 💾 Core Memory Management
- **Agent Memory**: Persistent profile and event storage for AI agents
- **User Memory**: Individual memory spaces for different users  
- **Profile Management**: Automatic profile updates based on conversations
- **Event Tracking**: Comprehensive conversation and interaction history
- **Theory of Mind**: Psychological analysis and behavioral insights

### 💬 Conversation Recording & Retrieval
- **Conversation Storage**: Structured conversation recording with required fields (user_id, agent_id, created_at)
- **Vector Embeddings**: High-quality semantic embeddings for conversations and messages
- **Semantic Search**: Intelligent conversation retrieval based on semantic similarity
- **Session Management**: Session-based conversation organization and tracking
- **Multiple Providers**: Support for OpenAI and SentenceTransformers embedding models

### 🧠 LLM Integration
- **Multiple LLM Providers**: OpenAI, Anthropic, Google Gemini, Azure OpenAI, Cohere, AWS Bedrock, Together AI, Replicate, Local LLMs
- **Intelligent Search**: LLM-powered search decision making and content analysis
- **Profile Updates**: AI-driven profile enhancement from conversation content
- **XML Parsing**: Structured profile output with automatic parsing

### 🔍 Advanced Search & Analysis
- **LLM-Enhanced Search**: Semantic understanding and relevance scoring
- **Vector Similarity Search**: Fast and accurate conversation retrieval
- **Intent Analysis**: Intelligent extraction of search requirements
- **Context-Aware Results**: Ranked results based on conversation context

## 📦 Installation

```bash
git clone https://github.com/NevaMind-AI/PersonaLab.git
cd PersonaLab
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
pre-commit install
```

### Optional: OpenAI Setup for Enhanced Embeddings

```bash
pip install openai
export OPENAI_API_KEY="your-api-key-here"
```

## 🚀 Quick Start

### Basic Memory Management

```python
from personalab.memory import MemoryManager

# Create memory manager
memory_manager = MemoryManager()

# Get or create agent memory
memory = memory_manager.get_or_create_memory("agent_123")

# Update memory with conversation
conversation = [
    {"role": "user", "content": "I'm learning machine learning"},
    {"role": "assistant", "content": "That's great! What specific areas interest you?"}
]

updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
    "agent_123", 
    conversation
)

print(f"Updated profile: {updated_memory.get_profile_content()}")
print(f"Events: {updated_memory.get_event_content()}")
print(f"ToM insights: {updated_memory.get_tom_content()}")
```

### Conversation Recording & Semantic Search

```python
from personalab.memo import ConversationManager

# Initialize conversation manager with embeddings
manager = ConversationManager(
    db_path="conversations.db",
    enable_embeddings=True,
    embedding_provider="auto"  # Automatically selects best available
)

# Record a conversation (user_id and agent_id are required)
conversation = manager.record_conversation(
    agent_id="assistant_v1",
    user_id="user_123", 
    messages=[
        {"role": "user", "content": "How do I learn Python programming?"},
        {"role": "assistant", "content": "Start with basic syntax, then practice with projects."},
        {"role": "user", "content": "Any recommended resources?"},
        {"role": "assistant", "content": "Try Python.org tutorials and Codecademy."}
    ],
    enable_vectorization=True
)

# Search for similar conversations
results = manager.search_similar_conversations(
    agent_id="assistant_v1",
    query="Python learning resources",
    limit=5,
    similarity_threshold=0.7
)

for result in results:
    print(f"Similarity: {result['similarity_score']:.3f}")
    print(f"Summary: {result['summary']}")
    print("---")
```

### User-Based Conversation Filtering

```python
# Get conversation history for specific user
user_conversations = manager.get_conversation_history(
    agent_id="assistant_v1",
    user_id="user_123",
    limit=10
)

# Get conversations from specific session
session_conversations = manager.get_session_conversations(
    agent_id="assistant_v1",
    session_id="session_abc",
    user_id="user_123"
)
```



## 🏗️ Architecture

### Project Structure
```
PersonaLab/
├── personalab/
│   ├── __init__.py          # Main exports
│   ├── config.py            # Configuration management
│   ├── llm.py               # LLM integration
│   ├── memory/              # Core memory management module
│   │   ├── __init__.py      # Memory module exports
│   │   ├── base.py          # Core Memory, ProfileMemory, EventMemory, ToMMemory
│   │   ├── manager.py       # MemoryManager and conversation processing
│   │   ├── pipeline.py      # MemoryUpdatePipeline and pipeline stages
│   │   ├── storage.py       # MemoryRepository and database operations
│   │   ├── events.py        # Event-related utilities
│   │   └── profile.py       # Profile-related utilities
│   └── memo/                # Conversation recording and retrieval module
│       ├── __init__.py      # Memo module exports
│       ├── models.py        # Conversation and Message data models
│       ├── storage.py       # ConversationDB and vector storage
│       ├── manager.py       # ConversationManager and search functionality
│       └── embeddings.py    # Embedding providers and management
├── examples/                # Example scripts and usage demos
├── docs/                    # Documentation
└── tests/                   # Test suite
```

### Core Components

#### Memory Module (`personalab.memory`)
- **Memory**: Unified memory class with ProfileMemory, EventMemory, and ToMMemory
- **MemoryManager**: Complete memory lifecycle management
- **MemoryUpdatePipeline**: Three-stage LLM-driven update process
- **MemoryRepository**: SQLite-based persistent storage

#### Memo Module (`personalab.memo`)
- **ConversationManager**: High-level conversation recording and search
- **ConversationDB**: Database operations for conversations and vectors
- **Conversation/ConversationMessage**: Data models with required fields
- **EmbeddingProviders**: OpenAI, SentenceTransformers, auto-selection

### Required Fields for Conversations

All conversations must include these mandatory fields:
- **`agent_id`**: Unique identifier for the AI agent (required, non-empty)
- **`user_id`**: Unique identifier for the user (required, non-empty)  
- **`created_at`**: Timestamp (automatically set when conversation is created)

### Embedding Providers

PersonaLab supports multiple embedding providers with automatic fallback:

1. **OpenAI** (Premium): `text-embedding-ada-002` (1536 dimensions)
2. **SentenceTransformers** (Free): Local models like `all-MiniLM-L6-v2` (384 dimensions)
3. **Auto**: Automatically selects the best available provider

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI (for enhanced embeddings)
export OPENAI_API_KEY="your-openai-api-key"

# Other LLM providers
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_AI_API_KEY="your-google-key"
```

### Embedding Provider Configuration

```python
# Use specific embedding provider
manager = ConversationManager(
    embedding_provider="openai"  # or "sentence-transformers", "auto"
)

# Disable embeddings entirely
manager = ConversationManager(enable_embeddings=False)
```

### Memory Configuration

```python
# Custom memory manager setup
memory_manager = MemoryManager(
    db_path="custom_memory.db",
    llm_client=custom_llm,
    temperature=0.3,
    max_tokens=2000
)
```

### Search Parameters

```python
# Configure semantic search
results = manager.search_similar_conversations(
    agent_id="assistant",
    query="machine learning help",
    limit=10,                    # Maximum results
    similarity_threshold=0.7     # Minimum similarity score (0.0-1.0)
)
```

## 📚 Examples

The `examples/` directory contains comprehensive usage examples:

- **`memo_simple_example.py`**: Basic conversation recording and search
- **`conversation_retrieval_example.py`**: Advanced semantic search demonstrations
- **`simple_embedding_demo.py`**: Step-by-step embedding workflow
- **`conversation_validation_example.py`**: Required field validation testing
- **`quick_start.py`**: Integration of memory and memo systems
- **`memo_openai_embedding_example.py`**: OpenAI embedding optimization

## 🔍 Use Cases

### Customer Support
```python
# Record support conversations
support_conv = manager.record_conversation(
    agent_id="support_bot",
    user_id="customer_456",
    messages=conversation_data
)

# Find similar past issues
similar_issues = manager.search_similar_conversations(
    agent_id="support_bot", 
    query="login problems",
    similarity_threshold=0.8
)
```

### Educational Assistants
```python
# Track learning conversations
learning_conv = manager.record_conversation(
    agent_id="tutor_bot",
    user_id="student_789",
    messages=tutoring_session
)

# Retrieve related learning materials
related_topics = manager.search_similar_conversations(
    agent_id="tutor_bot",
    query="algebra word problems",
    user_id="student_789"  # User-specific search
)
```

### Personal AI Assistants
```python
# Maintain conversation history
personal_conv = manager.record_conversation(
    agent_id="personal_ai",
    user_id="user_personal",
    messages=daily_conversation,
    session_id="morning_chat"
)

# Contextual memory retrieval
context = manager.search_similar_conversations(
    agent_id="personal_ai",
    query="previous vacation plans",
    user_id="user_personal"
)
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test files
python -m pytest tests/test_memory.py
python -m pytest tests/test_memo.py

# Run with coverage
python -m pytest --cov=personalab tests/
```

## 📖 Documentation

For detailed documentation, see the `docs/` directory:

- **[OpenAI Setup Guide](docs/OPENAI_SETUP.md)**: Configure OpenAI embeddings
- **[Embedding Providers](docs/EMBEDDING_PROVIDERS.md)**: Compare embedding options
- **API Reference**: Detailed method documentation

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing excellent embedding models
- SentenceTransformers team for open-source embedding solutions
- Contributors and the AI/ML community for inspiration and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/NevaMind-AI/PersonaLab/issues)
- **Discussions**: [GitHub Discussions](https://github.com/NevaMind-AI/PersonaLab/discussions)
- **Documentation**: [docs/](docs/) directory

---

**PersonaLab** - Building the memory foundation for next-generation AI agents 🧠✨ 