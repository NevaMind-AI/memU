<div align="center">

![PersonaLab Banner](assets/banner.png)
  
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

> **Important Note**: All PersonaLab chat interactions require a `user_id` parameter to identify different users and maintain separate memory spaces for each user.

### Usage (3 lines of code!)

```python
from personalab import Persona
from personalab.llm import OpenAIClient, AnthropicClient

# Method 1: Pass llm_client directly
openai_client = OpenAIClient(api_key="your-key", model="gpt-4")
persona = Persona(agent_id="my_ai_assistant", llm_client=openai_client)

# Or with Anthropic
anthropic_client = AnthropicClient(api_key="your-key")
persona = Persona(agent_id="claude_assistant", llm_client=anthropic_client)

# Method 2: Simple default usage (reads OPENAI_API_KEY from .env)
persona = Persona(agent_id="my_ai_assistant")

# Configure features
persona = Persona(
    agent_id="my_ai_assistant",
    llm_client=openai_client,  # Pass your configured LLM client
    personality="You are a helpful and friendly programming tutor.",  # 🎭 AI personality
    use_memory=True,   # 🧠 Long-term memory (facts, preferences, events)
    use_memo=True      # 💬 Conversation history & semantic search
)

def chat_with_memories(message: str, user_id: str) -> str:
    return persona.chat(message, user_id=user_id)

# That's it! Your AI now has persistent memory and conversation retrieval
user_id = "student_123"
print(chat_with_memories("Hi, I'm learning Python", user_id))
print(chat_with_memories("What was I learning?", user_id))  # Remembers previous context

# Don't forget to call endsession to update memories
persona.endsession(user_id)

# The conversations are automatically stored as events in memory
# and recorded in memo for semantic search retrieval
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
from personalab import Persona
from personalab.llm import OpenAIClient

# Create persona with memory enabled
persona = Persona(
    agent_id="my_assistant",
    use_memory=True,
    use_memo=True
)

# Chat with the AI
user_id = "user_123"
response1 = persona.chat("I'm learning machine learning", user_id=user_id)
response2 = persona.chat("What specific areas should I focus on?", user_id=user_id)

# End session to update memories
result = persona.endsession(user_id)
print(f"Memory update result: {result}")

# Get memory information
memory_info = persona.get_memory(user_id)
print(f"Profile: {memory_info['profile']}")
print(f"Events: {len(memory_info['events'])} stored")
print(f"Mind insights: {len(memory_info['mind'])} stored")
```

### Conversation Recording & Semantic Search

```python
from personalab import Persona, ConversationManager

# Method 1: Using Persona (recommended - automatic conversation management)
persona = Persona(
    agent_id="assistant_v1",
    use_memo=True,  # Enable conversation recording
    show_retrieval=True  # Show when relevant conversations are retrieved
)

user_id = "user_123"

# Chat automatically records and retrieves relevant conversations
response1 = persona.chat("How do I learn Python programming?", user_id=user_id)
response2 = persona.chat("Any recommended resources?", user_id=user_id)

# Search for similar conversations manually
results = persona.search("Python tutorials", user_id=user_id, top_k=5)
for result in results:
    print(f"Found: {result.get('summary', 'No summary')}")

# Method 2: Direct ConversationManager usage
manager = ConversationManager(
    enable_embeddings=True,
    embedding_provider="auto"  # Automatically selects best available
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
# Using Persona for user-specific operations
persona = Persona(agent_id="assistant_v1")
user_id = "user_123"

# Get session information for user
session_info = persona.get_session_info(user_id)
print(f"Messages in current session: {session_info['total_messages']}")

# Search conversations for specific user
user_results = persona.search("learning goals", user_id=user_id, top_k=10)

# Using ConversationManager directly
manager = ConversationManager()

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
│   │   ├── base.py          # Core Memory, ProfileMemory, EventMemory, MindMemory
│   │   ├── manager.py       # MemoryManager and conversation processing
│   │   ├── pipeline.py      # MemoryUpdatePipeline and pipeline stages
│   │   ├── storage.py       # MemoryDB and database operations
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
- **Memory**: Unified memory class with ProfileMemory, EventMemory, and MindMemory
- **MemoryManager**: Complete memory lifecycle management
- **MemoryUpdatePipeline**: Three-stage LLM-driven update process
- **MemoryDB**: PostgreSQL-based persistent storage

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
# Custom persona setup with specific LLM configuration
from personalab.llm import OpenAIClient

custom_llm = OpenAIClient(
    api_key="your-key",
    model="gpt-4",
    temperature=0.3,
    max_tokens=2000
)

persona = Persona(
    agent_id="custom_assistant",
    llm_client=custom_llm,
    use_memory=True,
    use_memo=True,
    show_retrieval=False
)
```

### Search Parameters

```python
# Configure semantic search using Persona
persona = Persona(agent_id="assistant")
user_id = "user_123"

# Search with parameters
results = persona.search(
    query="machine learning help",
    user_id=user_id,
    top_k=10                     # Maximum results
)

# Or using ConversationManager directly for more control
manager = ConversationManager()
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
# Create support persona
support_persona = Persona(
    agent_id="support_bot",
    personality="You are a helpful customer support agent.",
    use_memory=True,
    use_memo=True
)

customer_id = "customer_456"

# Handle customer inquiry (automatically records and retrieves context)
response = support_persona.chat("I'm having login problems", user_id=customer_id)

# Find similar past issues
similar_issues = support_persona.search("login problems", user_id=customer_id, top_k=5)

# End session to update customer profile
support_persona.endsession(customer_id)
```

### Educational Assistants
```python
# Create tutor persona
tutor_persona = Persona(
    agent_id="tutor_bot",
    personality="You are a patient and encouraging math tutor.",
    use_memory=True,
    use_memo=True
)

student_id = "student_789"

# Tutoring session (automatically tracks learning progress)
response1 = tutor_persona.chat("I need help with algebra word problems", user_id=student_id)
response2 = tutor_persona.chat("Can you give me another example?", user_id=student_id)

# Retrieve related learning materials from past sessions
related_topics = tutor_persona.search("algebra word problems", user_id=student_id, top_k=5)

# End session to update learning profile
result = tutor_persona.endsession(student_id)
print(f"Learning progress updated: {result}")
```

### Personal AI Assistants
```python
# Create personal assistant
personal_assistant = Persona(
    agent_id="personal_ai",
    personality="You are a thoughtful personal assistant who remembers important details.",
    use_memory=True,
    use_memo=True
)

user_id = "user_personal"

# Daily conversation with memory
with personal_assistant.session(user_id):
    response1 = personal_assistant.chat("I'm planning a vacation to Japan", user_id=user_id)
    response2 = personal_assistant.chat("What should I pack?", user_id=user_id)
    # Session automatically ends and updates memory

# Later conversation - retrieves context automatically
response3 = personal_assistant.chat("What were those vacation plans I mentioned?", user_id=user_id)

# Manual context retrieval if needed
context = personal_assistant.search("vacation plans", user_id=user_id, top_k=3)
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

## 🔄 CI/CD Status

This project uses GitHub Actions for continuous integration and automated PyPI publishing.

- **CI Workflow**: Runs on every push to `main` and `develop` branches
- **Publish Workflow**: Runs on GitHub releases or manual trigger
- **Code Quality**: Black, isort, flake8, mypy checks
- **Testing**: Pytest with PostgreSQL integration

[![CI](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/ci.yml/badge.svg)](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/ci.yml)
[![Publish](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/publish.yml/badge.svg)](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/publish.yml) 