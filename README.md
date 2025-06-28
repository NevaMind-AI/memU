# PersonaLab

PersonaLab is an advanced AI memory management system that provides intelligent profile management and LLM-enhanced search capabilities for AI agents. It offers persistent memory storage, conversation analysis, and psychological modeling through Theory of Mind (ToM) capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Features

### 📝 Core Memory Management
- **Agent Memory**: Persistent profile and event storage for AI agents
- **User Memory**: Individual memory spaces for different users
- **Profile Management**: Automatic profile updates based on conversations
- **Event Tracking**: Comprehensive conversation and interaction history
- **Theory of Mind**: Psychological analysis and insights generation

### 🧠 LLM Integration
- **Multiple LLM Providers**: OpenAI, Anthropic, Google Gemini, Azure OpenAI, Cohere, AWS Bedrock, Together AI, Replicate, Local LLMs
- **Intelligent Search**: LLM-powered search decision making and content analysis
- **Profile Updates**: AI-driven profile enhancement from conversation content
- **XML Parsing**: Structured profile output with automatic parsing

### 🔍 Advanced Search
- **LLM-Enhanced Search**: Semantic understanding and relevance scoring
- **Deep Search**: Multi-level content analysis with cross-referencing
- **Intent Analysis**: Intelligent extraction of search requirements
- **Context-Aware Results**: Ranked results based on conversation context

### 🏗️ Unified Memory Architecture
- **Unified Memory Class**: Integrated ProfileMemory, EventMemory, and ToMMemory components
- **Pipeline-Based Updates**: Three-stage update process (Modification → Update → Theory of Mind)
- **Database Storage**: SQLite-based persistent storage with efficient querying
- **Memory Manager**: Complete lifecycle management with conversation processing

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

## 🛠️ Quick Start

### Basic Usage

```python
from personalab.main import Memory

# Create a memory instance
memory = Memory("my_agent", enable_llm_search=True)

# Set initial agent profile
agent_memory = memory.get_agent_memory()
agent_memory.update_profile("I am an AI assistant specialized in programming.")

# Add events
agent_memory.update_events(["User asked about Python programming best practices."])

# Search memory
if memory.need_search("Tell me about Python coding"):
    results = memory.deep_search("What Python topics have we discussed?")
    print(results['relevant_context'])
```

### Using the New Unified Architecture

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

### Profile Updates

```python
# Update agent profile based on conversation
conversation = """
User: Can you help with machine learning?
Agent: Yes! I have experience with scikit-learn, PyTorch, and TensorFlow.
"""

updated_profile = memory.update_agent_profile_memory(conversation)
print(f"Updated profile: {updated_profile}")

# Update user profile
user_id = "data_scientist_alice"
updated_user_profile = memory.update_user_profile_memory(user_id, conversation)
```

### LLM Provider Setup

```python
from personalab.llm import LLMManager

# Quick setup (auto-detects available providers)
llm_manager = LLMManager.create_quick_setup()

# Use specific provider
memory = Memory("agent", llm_instance=llm_manager.get_current_provider())
```

## 🏗️ Architecture

### Memory Structure
```
PersonaLab/
├── personalab/
│   ├── main.py              # Legacy Memory class (backward compatibility)
│   ├── config.py            # Configuration management
│   ├── llm.py               # LLM integration
│   └── memory/              # New unified memory architecture
│       ├── __init__.py      # Memory module exports
│       ├── base.py          # Core Memory, ProfileMemory, EventMemory, ToMMemory
│       ├── manager.py       # MemoryManager and ConversationMemoryInterface
│       ├── pipeline.py      # MemoryUpdatePipeline and pipeline stages
│       ├── storage.py       # MemoryRepository and database operations
│       ├── events.py        # Event-related utilities
│       ├── profile.py       # Profile-related utilities
│ 
└── examples/                # Example scripts and usage demos
```

### Key Components

- **Memory**: Unified memory class containing ProfileMemory, EventMemory, and ToMMemory components
- **MemoryManager**: Handles complete memory lifecycle including database operations
- **MemoryUpdatePipeline**: Three-stage LLM-driven update process
- **LLMManager**: Handles multiple LLM provider integrations
- **Search System**: LLM-powered intelligent search and ranking

### Memory Update Pipeline

The system uses a sophisticated three-stage pipeline for updating memories:

1. **Modification Stage**: Analyzes conversation content and extracts relevant information
2. **Update Stage**: Updates profile and events based on extracted information
3. **Theory of Mind Stage**: Performs psychological analysis and generates insights

## 🔧 Configuration

### LLM Settings

```python
# Enable/disable LLM-based search
memory = Memory("agent", enable_llm_search=True)

# Use custom LLM instance
from personalab.llm import OpenAILLM
custom_llm = OpenAILLM(api_key="your-key")
memory = Memory("agent", llm_instance=custom_llm)
```

### Search Parameters

```python
# Configure deep search
results = memory.deep_search(
    conversation="What did we discuss about AI?",
    max_results=10,
    similarity_threshold=70.0
)
```

### Memory Manager Configuration

```python
# Configure memory manager
memory_manager = MemoryManager(
    db_path="custom_memory.db",
    llm_client=custom_llm,
    temperature=0.3,
    max_tokens=2000
)
```

## 📊 API Reference

### Memory Class (Legacy)

- `Memory(agent_id, enable_llm_search=True, llm_instance=None)`
- `need_search(conversation, system_prompt="", context_length=0) -> bool`
- `deep_search(conversation, system_prompt="", user_id=None, max_results=15) -> Dict`
- `update_agent_profile_memory(conversation) -> str`
- `update_user_profile_memory(user_id, conversation) -> str`

### MemoryManager (New Architecture)

- `MemoryManager(db_path="memory.db", llm_client=None, **llm_config)`
- `get_or_create_memory(agent_id) -> Memory`
- `update_memory_with_conversation(agent_id, conversation) -> Tuple[Memory, PipelineResult]`
- `get_memory_prompt(agent_id) -> str`
- `update_profile(agent_id, profile_info) -> bool`
- `add_events(agent_id, events) -> bool`

### Unified Memory

- `Memory(agent_id, memory_id=None)`
- `get_profile_content() -> str`
- `get_event_content() -> List[str]`
- `get_tom_content() -> List[str]`
- `update_profile(new_profile_info)`
- `update_events(new_events)`
- `update_tom(new_insights)`
- `to_prompt() -> str`

### LLM Manager

- `LLMManager.create_quick_setup() -> LLMManager`
- `add_provider(provider_name, llm_instance)`
- `switch_provider(provider_name) -> bool`
- `get_current_provider() -> BaseLLM`

## 🎯 Use Cases

- **AI Chatbots**: Persistent memory and context awareness
- **Personal Assistants**: User preference learning and adaptation
- **Customer Service**: Agent knowledge base and user history tracking
- **Educational Systems**: Student progress tracking and personalization
- **Research Tools**: Information organization and intelligent retrieval
- **Multi-Agent Systems**: Inter-agent memory sharing and coordination

## 🧪 Examples

### Memory + OpenAI Integration

See the `examples/` directory for comprehensive integration examples:

- **`quick_start.py`**: Simplest possible PersonaLab + OpenAI integration
- **`memory_chat_integration.py`**: Complete memory-enhanced chatbot with:
  - Interactive chat interface
  - Automatic memory updates
  - Conversation history management
  - Memory export/import

```bash
# Quick start
python examples/quick_start.py

# Interactive demo
python examples/memory_chat_integration.py demo

# Programmatic example
python examples/memory_chat_integration.py programmatic
```

### Core Memory Examples

- `simple_memory_example.py`: Basic memory operations
- `pipeline_debug_example.py`: Pipeline debugging and inspection
- `tom_memory_example.py`: Theory of Mind capabilities
- `stage_by_stage_example.py`: Step-by-step pipeline execution
- `example_memory_update.py`: Advanced memory update scenarios

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=personalab --cov-report=term-missing

# Run specific test file
pytest tests/test_memory.py
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install development dependencies: `pip install -r requirements-dev.txt`
5. Install pre-commit hooks: `pre-commit install`
6. Make your changes and run tests: `pytest`
7. Submit a pull request

### Code Style

We use:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **Pre-commit** for automated checks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Acknowledgments

- Built with modern Python practices and design patterns
- Integrated with leading LLM providers for maximum flexibility
- Designed for production use with robust error handling
- Inspired by cognitive science and psychology research

## 📚 Documentation

For detailed documentation, please visit our [Documentation Site](https://nevamind-ai.github.io/PersonaLab/) (coming soon).

## 🐛 Bug Reports and Feature Requests

Please use our [GitHub Issues](https://github.com/NevaMind-AI/PersonaLab/issues) to report bugs or request features.

## 💬 Support

- 📧 Email: support@nevamind.ai
- 💬 Discord: [Join our community](https://discord.gg/nevamind)
- 📚 Documentation: [docs.nevamind.ai](https://docs.nevamind.ai) 