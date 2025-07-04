<div align="center">

![PersonaLab Banner](assets/banner.png)
  
# PersonaLab

🧠 **AI Memory and Conversation Management Framework** - Simple as mem0, Powerful as PersonaLab

[![PyPI version](https://badge.fury.io/py/personalab.svg)](https://badge.fury.io/py/personalab)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/ci.yml/badge.svg)](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/ci.yml)
[![Publish](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/publish.yml/badge.svg)](https://github.com/NevaMind-AI/PersonaLab/actions/workflows/publish.yml)

</div>

> 🎉 **PersonaLab v0.1.0 is now available on PyPI!** - The first official release with stable PostgreSQL-based memory system and multi-LLM support.

PersonaLab is a comprehensive AI memory and conversation management system that provides intelligent profile management, conversation recording, and advanced semantic search capabilities for AI agents. It combines persistent memory storage, conversation analysis, psychological modeling, and vector-based retrieval for building sophisticated AI applications.

## 📦 Installation

### From PyPI (Recommended)

```bash
# Basic installation
pip install personalab

# With AI features (includes OpenAI support)
pip install personalab[ai]

# Full installation (all LLM providers and features)
pip install personalab[all]
```

### From Source (Development)

```bash
git clone https://github.com/NevaMind-AI/PersonaLab.git
cd PersonaLab
pip install -e .

# For development
pip install -r requirements-dev.txt
pre-commit install
```

## ⚡ Quick Start

> **💡 Important**: All PersonaLab chat interactions require a `user_id` parameter to identify different users and maintain separate memory spaces for each user.

### Simple 3-Line Setup

```python
from personalab import Persona

# Create an AI persona with memory
persona = Persona(agent_id="my_assistant")

# Chat with persistent memory across sessions
response = persona.chat("Hi, I'm learning Python", user_id="student_123")
print(response)

# Memory is automatically managed!
```

### Complete Example with Memory & LLM Configuration

```python
from personalab import Persona
from personalab.llm import OpenAIClient, AnthropicClient

# Configure your LLM client
openai_client = OpenAIClient(api_key="your-key", model="gpt-4")

# Create persona with full features
persona = Persona(
    agent_id="programming_tutor",
    llm_client=openai_client,
    personality="You are a helpful and friendly programming tutor.",
    use_memory=True,   # 🧠 Long-term memory (facts, preferences, events)
    use_memo=True      # 💬 Conversation history & semantic search
)

# Chat with memory
user_id = "student_123"
response1 = persona.chat("I'm learning machine learning", user_id=user_id)
response2 = persona.chat("What did I mention I was learning?", user_id=user_id)

# End session to update memories
persona.endsession(user_id)

# Get stored memories
memory_info = persona.get_memory(user_id)
print(f"Profile: {memory_info['profile']}")
print(f"Events: {len(memory_info['events'])} stored")
```

### Environment Setup

```bash
# 1. Copy environment template (if using from source)
cp .env.example .env

# 2. Add your API keys to .env
echo "OPENAI_API_KEY=your_openai_key_here" >> .env
echo "ANTHROPIC_API_KEY=your_anthropic_key_here" >> .env

# 3. Test configuration
python -c "from personalab import Persona; print('✅ PersonaLab ready!')"
```

## 🌟 Key Features

### 💾 Intelligent Memory System
- **🧠 Agent Memory**: Persistent profile and event storage for AI agents
- **👤 User Memory**: Individual memory spaces for different users  
- **📝 Profile Management**: Automatic profile updates based on conversations
- **📚 Event Tracking**: Comprehensive conversation and interaction history
- **🧠 Theory of Mind**: Psychological analysis and behavioral insights

### 💬 Advanced Conversation Management
- **📝 Conversation Storage**: Structured recording with metadata (user_id, agent_id, timestamps)
- **🔍 Vector Embeddings**: High-quality semantic embeddings for intelligent search
- **🎯 Semantic Search**: Retrieve relevant conversations based on meaning, not just keywords
- **🔄 Session Management**: Organized conversation tracking and session handling
- **⚡ Multiple Providers**: OpenAI, SentenceTransformers, and more embedding options

### 🤖 Multi-LLM Integration
- **🌐 Multiple Providers**: OpenAI, Anthropic, Google Gemini, Azure OpenAI, Cohere, AWS Bedrock, Together AI, Replicate
- **🔍 Intelligent Search**: LLM-powered decision making and content analysis
- **📊 Profile Updates**: AI-driven profile enhancement from conversation content
- **🔧 Flexible Configuration**: Easy switching between LLM providers and models

### 🔍 Advanced Search & Analysis
- **🧠 LLM-Enhanced Search**: Semantic understanding and relevance scoring
- **⚡ Vector Similarity**: Fast and accurate conversation retrieval
- **🎯 Intent Analysis**: Intelligent extraction of search requirements
- **📊 Context-Aware Results**: Ranked results based on conversation context

## 📋 Requirements

- **Python**: 3.8 or higher
- **Database**: PostgreSQL (required for memory storage)
- **LLM API Keys**: OpenAI, Anthropic, or other supported providers

### Database Setup

PersonaLab requires PostgreSQL for memory storage. Quick setup:

```bash
# Using Docker (recommended)
docker run --name personalab-postgres -e POSTGRES_PASSWORD=your_password -p 5432:5432 -d postgres:14

# Or install PostgreSQL locally
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql
# Windows: Download from https://www.postgresql.org/download/
```

## 💡 Advanced Usage Examples

### Memory & Conversation Integration

```python
from personalab import Persona
from personalab.llm import OpenAIClient, AnthropicClient

# Example 1: Educational Tutor with Memory
tutor = Persona(
    agent_id="math_tutor",
    personality="You are a patient math tutor who tracks student progress.",
    use_memory=True,  # Remember student profiles and learning history
    use_memo=True,    # Search previous conversations for context
    show_retrieval=True  # Show when retrieving relevant past conversations
)

student_id = "student_123"

# First lesson
response1 = tutor.chat("I'm struggling with algebra", user_id=student_id)
response2 = tutor.chat("Can you explain linear equations?", user_id=student_id)

# Later lesson - automatically retrieves relevant context
response3 = tutor.chat("I forgot what we learned about equations", user_id=student_id)

# Update student profile with progress
tutor.endsession(student_id)

# Example 2: Customer Support with Different LLM
support = Persona(
    agent_id="support_agent",
    llm_client=AnthropicClient(api_key="your-key"),  # Using Claude
    personality="You are a helpful customer support specialist.",
    use_memory=True,
    use_memo=True
)

customer_id = "customer_456"
support_response = support.chat("My account is locked", user_id=customer_id)

# Search for similar support tickets
similar_tickets = support.search("account locked", user_id=customer_id, top_k=3)
```

### Direct ConversationManager Usage

```python
from personalab.memo import ConversationManager

# Advanced conversation search and analysis
manager = ConversationManager(
    enable_embeddings=True,
    embedding_provider="openai"  # Use OpenAI embeddings for better quality
)

# Search across all conversations for an agent
results = manager.search_similar_conversations(
    agent_id="support_agent",
    query="billing issues and refunds",
    limit=10,
    similarity_threshold=0.75  # Higher threshold for more relevant results
)

for result in results:
    print(f"Score: {result['similarity_score']:.3f}")
    print(f"User: {result['user_id']}")
    print(f"Summary: {result['summary']}")
    print("---")
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

The [`examples/`](examples/) directory contains comprehensive usage examples:

- **[`memo_simple_example.py`](examples/memo_simple_example.py)**: Basic conversation recording and search
- **[`conversation_retrieval_example.py`](examples/conversation_retrieval_example.py)**: Advanced semantic search demonstrations
- **[`simple_embedding_demo.py`](examples/simple_embedding_demo.py)**: Step-by-step embedding workflow
- **[`conversation_validation_example.py`](examples/conversation_validation_example.py)**: Required field validation testing
- **[`quick_start.py`](examples/quick_start.py)**: Integration of memory and memo systems
- **[`memo_openai_embedding_example.py`](examples/memo_openai_embedding_example.py)**: OpenAI embedding optimization

### 🚀 Try the Examples
```bash
# Clone the repository to access examples
git clone https://github.com/NevaMind-AI/PersonaLab.git
cd PersonaLab

# Set up environment
cp .env.example .env  # Add your API keys
pip install -e .

# Run examples
python examples/quick_start.py
python examples/memo_simple_example.py
```

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

## 📋 What's New in v0.1.0

🎉 **First Official Release!** PersonaLab v0.1.0 brings stable, production-ready AI memory management:

### ✨ Key Features
- **🗄️ PostgreSQL-Only Architecture**: Removed all SQLite dependencies for production reliability
- **🧠 Enhanced Memory System**: Improved profile updates and event tracking
- **💬 Advanced Conversation Search**: Semantic search with multiple embedding providers
- **🤖 Multi-LLM Support**: OpenAI, Anthropic, Google Gemini, and 8+ other providers
- **📦 PyPI Package**: Easy installation with `pip install personalab`
- **🔍 Better Documentation**: Comprehensive examples and usage guides
- **⚡ Performance Optimizations**: Faster memory updates and conversation retrieval

### 🛠️ Technical Improvements
- **Python 3.8+ Compatibility**: Tested across Python 3.8-3.12
- **Automated CI/CD**: GitHub Actions for testing and PyPI publishing
- **Code Quality**: Black, isort, flake8, mypy formatting standards
- **Comprehensive Testing**: Full test suite with PostgreSQL integration

### 🚀 Migration from Pre-release
If you're upgrading from development versions:
```bash
# Remove old development installation
pip uninstall personalab

# Install official release
pip install personalab[all]
```

### 📅 Release History
- **v0.1.0** (Current) - First official PyPI release with PostgreSQL-only architecture
- **Pre-release** - Development versions with SQLite support (deprecated)

### 🔗 Links
- **PyPI Package**: https://pypi.org/project/personalab/
- **GitHub Repository**: https://github.com/NevaMind-AI/PersonaLab
- **Documentation**: [docs/](docs/) directory
- **Examples**: [examples/](examples/) directory

---

**PersonaLab** - Building the memory foundation for next-generation AI agents 🧠✨ 