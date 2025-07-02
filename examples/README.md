# PersonaLab Examples

Welcome to PersonaLab examples! This directory contains comprehensive examples demonstrating how to use PersonaLab for building AI applications with memory and conversation capabilities.

## 📚 Example Overview

### 🚀 Quick Start
- **[01_quick_start.py](01_quick_start.py)** - The fastest way to get started with PersonaLab
  - Basic Persona usage
  - Automatic memory learning
  - Conversation search
  - Works with or without API keys

### 🧠 Memory Management
- **[02_memory_basics.py](02_memory_basics.py)** - Detailed memory operations
  - Manual memory management
  - Facts, preferences, and events
  - Memory persistence across sessions
  - Memory retrieval and testing

### 🔍 Conversation Retrieval
- **[03_conversation_retrieval.py](03_conversation_retrieval.py)** - Search and retrieval capabilities
  - Automatic conversation recording
  - Semantic search through history
  - Context-aware responses
  - Retrieval visibility controls

### ⚙️ Feature Combinations
- **[04_feature_combinations.py](04_feature_combinations.py)** - Different configuration options
  - Full Features (Memory + Memo)
  - Memory Only
  - Memo Only
  - Minimal (Pure LLM)
  - Performance comparisons

### 🚀 Advanced Usage
- **[05_advanced_usage.py](05_advanced_usage.py)** - Sophisticated patterns
  - Multi-LLM providers
  - Custom LLM functions
  - Error handling strategies
  - Multi-agent systems
  - Advanced memory patterns

### 🛠️ Custom LLM Integration
- **[06_custom_llm.py](06_custom_llm.py)** - Custom LLM implementations
  - Rule-based LLM functions
  - Template-based responses
  - Domain-specific behaviors
  - Local LLM integration patterns

### 🏭 Production Ready
- **[07_production_ready.py](07_production_ready.py)** - Enterprise deployment patterns
  - Production ChatBot class
  - Error handling and logging
  - Session management
  - Monitoring and analytics
  - Interactive chat interface

## 🏃‍♂️ Quick Start Guide

### Prerequisites

1. **Install PersonaLab:**
   ```bash
   pip install -e .
   ```

2. **Set up API keys (optional):**
   Create a `.env` file in the project root:
   ```bash
   # For OpenAI (default)
   OPENAI_API_KEY="your-openai-key"
   
   # OR for Anthropic
   ANTHROPIC_API_KEY="your-anthropic-key"
   ```

3. **Run any example:**
   ```bash
   python examples/01_quick_start.py
   ```

### Without API Keys

All examples work without API keys by using mock LLM functions for demonstration purposes. This allows you to:
- Learn PersonaLab concepts
- Test memory and retrieval features
- Understand different configuration options
- Prototype your applications

## 📖 Learning Path

### For Beginners
1. Start with **01_quick_start.py** to understand basic concepts
2. Try **02_memory_basics.py** to learn memory management
3. Explore **04_feature_combinations.py** to understand options

### For Developers
1. Review **03_conversation_retrieval.py** for search capabilities
2. Study **05_advanced_usage.py** for sophisticated patterns
3. Examine **06_custom_llm.py** for integration techniques

### For Production
1. Analyze **07_production_ready.py** for deployment patterns
2. Review configuration and error handling approaches
3. Understand session management and monitoring

## 🎯 Use Case Examples

### Personal Assistant
```python
from personalab import Persona

# Create a personal assistant with full features
assistant = Persona(
    agent_id="personal_assistant",
    use_memory=True,
    use_memo=True
)

# Have natural conversations
response = assistant.chat("I love hiking and photography")
memory = assistant.get_memory()  # See what it learned
```

### Customer Support Bot
```python
# Memory-only for learning user preferences
support_bot = Persona(
    agent_id="customer_support",
    use_memory=True,
    use_memo=False  # No conversation storage for privacy
)
```

### Educational Tutor
```python
# Full features for personalized learning
tutor = Persona(
    agent_id="math_tutor",
    use_memory=True,
    use_memo=True,
    show_retrieval=True  # Show how it uses past conversations
)
```

### Simple Chatbot
```python
# Minimal configuration for basic interactions
chatbot = Persona(
    agent_id="simple_bot",
    use_memory=False,
    use_memo=False  # Stateless conversations
)
```

## 🔧 Configuration Options

### LLM Providers
```python
# OpenAI (default)
persona = Persona(agent_id="user")

# Anthropic
persona = Persona.create_anthropic(agent_id="user")

# Custom LLM
def my_llm_function(messages, **kwargs):
    return "Custom response"

persona = Persona.create_custom(
    agent_id="user",
    llm_function=my_llm_function
)
```

### Feature Control
```python
persona = Persona(
    agent_id="user",
    use_memory=True,      # Long-term memory learning
    use_memo=True,        # Conversation storage & retrieval
    show_retrieval=False  # Hide retrieval process
)
```

## 🚀 Performance Guide

### Configuration Performance

| Configuration | LLM Calls | Memory Usage | Best For |
|---------------|-----------|--------------|----------|
| Full Features | 2 per conversation | High | Rich user experience |
| Memory Only | 1 per conversation | Medium | Learning without storage |
| Memo Only | 1 per conversation | Medium | Context without learning |
| Minimal | 1 per conversation | Low | Simple interactions |

### Optimization Tips

1. **Use Memory Only** for learning-focused applications
2. **Use Memo Only** for context-aware but privacy-conscious apps
3. **Use Minimal** for high-throughput, stateless interactions
4. **Use Full Features** for the best user experience

## 🛠️ Development Tips

### Error Handling
```python
try:
    response = persona.chat(message)
except Exception as e:
    # Handle LLM API errors gracefully
    response = "I'm experiencing technical difficulties. Please try again."
```

### Memory Management
```python
# Add facts manually
persona.add_memory("User prefers email over phone", memory_type="preferences")

# Check memory contents
memory = persona.get_memory()
print(f"Facts: {len(memory['facts'])}")
```

### Session Cleanup
```python
# Always close personas when done
persona.close()

# Or use context manager (if available)
with Persona(agent_id="user") as persona:
    response = persona.chat("Hello!")
```

## 🏗️ Architecture Patterns

### Single User Application
```python
# Simple single-user app
persona = Persona(agent_id="single_user")
```

### Multi-User Application
```python
# Manage multiple users
users = {}

def get_persona(user_id):
    if user_id not in users:
        users[user_id] = Persona(agent_id=user_id)
    return users[user_id]
```

### Microservice Integration
```python
# Service-oriented architecture
class PersonaService:
    def __init__(self):
        self.personas = {}
    
    def chat(self, user_id: str, message: str):
        persona = self.get_or_create_persona(user_id)
        return persona.chat(message)
```

## 📊 Monitoring and Analytics

### Basic Metrics
```python
# Track conversation metrics
memory = persona.get_memory()
metrics = {
    'facts_count': len(memory['facts']),
    'conversation_count': len(memory['events']),
    'last_activity': datetime.now()
}
```

### Advanced Monitoring
See `07_production_ready.py` for comprehensive monitoring patterns including:
- Session statistics
- Error tracking
- Performance metrics
- System health checks

## 🤝 Contributing

To add new examples:

1. Follow the naming convention: `XX_example_name.py`
2. Include comprehensive docstrings
3. Provide both API key and mock LLM versions
4. Add error handling demonstrations
5. Update this README with your example

## 📧 Support

- **Documentation**: Check the main README and docstrings
- **Examples**: All examples include detailed comments
- **Issues**: Report problems via GitHub issues
- **Discussions**: Join community discussions for questions

## 🔗 Related Resources

- [PersonaLab Documentation](../README.md)
- [API Reference](../docs/)
- [Contributing Guide](../CONTRIBUTING.md)
- [License](../LICENSE) 