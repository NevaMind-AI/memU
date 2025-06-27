# PersonaLab

PersonaLab is an advanced memory management system for AI agents that provides intelligent profile management and LLM-enhanced search capabilities.

## 🚀 Features

### 📝 Core Memory Management
- **Agent Memory**: Persistent profile and event storage for AI agents
- **User Memory**: Individual memory spaces for different users
- **Profile Management**: Automatic profile updates based on conversations
- **Event Tracking**: Comprehensive conversation and interaction history

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

## 📦 Installation

```bash
git clone https://github.com/NevaMind-AI/PersonaLab.git
cd PersonaLab
pip install -r requirements.txt
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
│   ├── main.py              # Main Memory class
│   │   └── ...              # Other components
│   └── llm/                 # LLM integrations
│       └── ...              # Other providers
```

### Key Components

- **Memory**: Main interface for all memory operations  
- **Unified Memory Architecture**: New architecture with ProfileMemory and EventMemory components
- **UserMemory**: Individual user profiles and interactions
- **LLMManager**: Handles multiple LLM provider integrations
- **Search System**: LLM-powered intelligent search and ranking

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

## 📊 API Reference

### Memory Class

- `Memory(agent_id, enable_llm_search=True, llm_instance=None)`
- `need_search(conversation, system_prompt="", context_length=0) -> bool`
- `deep_search(conversation, system_prompt="", user_id=None, max_results=15) -> Dict`
- `update_agent_profile_memory(conversation) -> str`
- `update_user_profile_memory(user_id, conversation) -> str`

### LLM Manager

- `LLMManager.create_quick_setup() -> LLMManager`
- `add_provider(provider_name, llm_instance)`
- `switch_provider(provider_name) -> bool`
- `get_current_provider() -> BaseLLM`

## 🎯 Use Cases

- **AI Chatbots**: Persistent memory and context awareness
- **Personal Assistants**: User preference learning and adaptation
- **Customer Service**: Agent knowledge base and user history
- **Educational Systems**: Student progress tracking and personalization
- **Research Tools**: Information organization and retrieval

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🌟 Acknowledgments

- Built with modern Python practices and design patterns
- Integrated with leading LLM providers for maximum flexibility
- Designed for production use with robust error handling 