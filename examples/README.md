# PersonaLab Memory + OpenAI Integration Examples

This directory contains comprehensive examples showing how to integrate PersonaLab's memory system with OpenAI's ChatGPT API to build intelligent, context-aware chatbots.

## 🚀 Quick Start

### Prerequisites

1. **Install required packages:**
```bash
pip install openai>=1.0.0 personalab python-dotenv
```

2. **Set up your OpenAI API key:**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-openai-api-key-here
```

### Run the Interactive Demo

```bash
cd examples
python memory_chat_integration.py demo
```

### Run the Programmatic Example

```bash
python memory_chat_integration.py programmatic
```

## 📁 Files Overview

### `memory_chat_integration.py`
A comprehensive example demonstrating:
- **Memory-enhanced chatbot class** with automatic memory updates
- **Interactive chat interface** with persistent memory
- **Programmatic usage** examples for integration into applications
- **Error handling and graceful fallbacks**
- **Memory export/import capabilities**

## 🔧 Core Integration Pattern

The key to integrating PersonaLab memory with OpenAI is using the `enhance_system_prompt_with_memory` utility function:

### Basic Usage

```python
from personalab.utils import enhance_system_prompt_with_memory
from personalab.memory import MemoryClient

# Initialize memory
memory_client = MemoryClient("chatbot.db")
memory = memory_client.get_memory_by_agent("user_001")

# Enhance system prompt with memory
base_prompt = "You are a helpful AI assistant."
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt=base_prompt,
    memory=memory,  # Can be Memory object or agent_id string
    include_profile=True,
    include_events=True,
    include_insights=True,
    max_events=8,
    max_insights=5
)

# Use with OpenAI
messages = [
    {"role": "system", "content": enhanced_prompt},
    {"role": "user", "content": "Hello!"}
]
```

### Advanced Integration Class

```python
class MemoryEnhancedChatbot:
    def __init__(self, agent_id: str, openai_api_key: str = None):
        self.agent_id = agent_id
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.memory_client = MemoryClient("memory.db")
        self.memory = self.memory_client.get_memory_by_agent(agent_id)
    
    def chat(self, user_message: str) -> str:
        # Get memory-enhanced system prompt
        system_prompt = enhance_system_prompt_with_memory(
            base_system_prompt="You are a helpful AI assistant.",
            memory=self.memory
        )
        
        # Call OpenAI API
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        assistant_response = response.choices[0].message.content
        
        # Update memory with conversation
        self._update_memory([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ])
        
        return assistant_response
    
    def _update_memory(self, conversation):
        updated_memory, _ = self.memory_client.update_memory_with_conversation(
            self.agent_id, 
            conversation
        )
        self.memory = updated_memory
```

## 🎯 Key Features

### 1. **Automatic Memory Updates**
The system automatically extracts and stores:
- **User profile information** (interests, preferences, background)
- **Conversation events** (important topics, decisions, plans)
- **Behavioral insights** (communication style, learning preferences)

### 2. **Memory-Enhanced Prompts**
The `enhance_system_prompt_with_memory` function:
- Adds relevant user context to system prompts
- Controls what memory content to include
- Limits context size for API efficiency
- Gracefully handles missing or empty memory

### 3. **Persistent Context**
- Memory persists across sessions
- SQLite database storage
- Export/import capabilities
- Memory statistics and analytics

## 🛠️ Configuration Options

### `enhance_system_prompt_with_memory` Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_system_prompt` | str | Required | Your base system prompt |
| `memory` | Memory or str | Required | Memory object or agent_id |
| `memory_client` | MemoryClient | None | Required if memory is agent_id |
| `include_profile` | bool | True | Include user profile information |
| `include_events` | bool | True | Include recent conversation events |
| `include_insights` | bool | True | Include behavioral insights |
| `max_events` | int | 10 | Maximum number of recent events |
| `max_insights` | int | 5 | Maximum number of recent insights |
| `memory_section_title` | str | "## Memory Context" | Title for memory section |

### Example with Custom Configuration

```python
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt="You are a coding mentor.",
    memory=memory,
    include_profile=True,
    include_events=True,
    include_insights=False,  # Skip behavioral insights
    max_events=5,           # Limit to 5 recent events
    max_insights=0,         # No insights
    memory_section_title="## Student Context"
)
```

## 💡 Best Practices

### 1. **Memory Management**
```python
# Check memory size periodically
memory_stats = memory_client.get_memory_stats(agent_id)
print(f"Total events: {memory_stats['total_events']}")

# Export memory for backup
memory_client.export_memory(agent_id, "backup.json")
```

### 2. **Error Handling**
```python
def safe_enhance_prompt(base_prompt, memory):
    try:
        return enhance_system_prompt_with_memory(
            base_system_prompt=base_prompt,
            memory=memory
        )
    except Exception as e:
        print(f"Memory enhancement failed: {e}")
        return base_prompt  # Fallback to base prompt
```

### 3. **Context Window Management**
```python
# For longer conversations, limit memory content
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt=base_prompt,
    memory=memory,
    max_events=3,      # Fewer events for longer chats
    max_insights=2     # Fewer insights to save tokens
)
```

### 4. **Selective Memory Updates**
```python
# Don't update memory for every interaction
response = chatbot.chat(user_message, update_memory=False)

# Update only for meaningful conversations
if is_meaningful_conversation(user_message, response):
    chatbot._update_memory_from_conversation([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response}
    ])
```

## 🔍 Memory Content Structure

The enhanced prompt includes three types of memory content:

### 1. **User Profile**
```
**User Profile:**
Software developer with 5 years of Python experience. Interested in AI/ML, 
prefers practical examples, works remotely.
```

### 2. **Recent Events**
```
**Recent Events:**
- Asked about FastAPI performance optimization
- Discussed async database patterns
- Explored vector database integration
```

### 3. **Behavioral Insights**
```
**Behavioral Insights:**
- Prefers concise, actionable responses
- Learns best through working code examples
- Asks follow-up questions for clarification
```

## 🚨 Common Issues & Solutions

### Issue: API Key Not Found
```python
# Solution: Check environment variable
import os
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Set OPENAI_API_KEY environment variable")
```

### Issue: Memory Not Updating
```python
# Solution: Verify memory client configuration
memory_client = MemoryClient("memory.db")
memory = memory_client.get_memory_by_agent(agent_id)

# Check if memory exists
if memory is None:
    print(f"No memory found for agent: {agent_id}")
```

### Issue: Token Limit Exceeded
```python
# Solution: Reduce memory content
enhanced_prompt = enhance_system_prompt_with_memory(
    base_system_prompt=base_prompt,
    memory=memory,
    max_events=3,      # Reduce events
    max_insights=2,    # Reduce insights
    include_profile=True  # Keep profile as it's usually concise
)
```

## 📊 Performance Tips

1. **Use appropriate max_events/max_insights** to control prompt size
2. **Cache enhanced prompts** when memory hasn't changed
3. **Use gpt-3.5-turbo** for faster, cheaper responses
4. **Implement conversation history limits** (e.g., last 20 messages)
5. **Consider async API calls** for better performance

## 🔄 Integration Workflow

```mermaid
graph LR
    A[User Message] --> B[Load Memory]
    B --> C[Enhance System Prompt]
    C --> D[Call OpenAI API]
    D --> E[Get Response]
    E --> F[Update Memory]
    F --> G[Return Response]
```

## 📚 Additional Resources

- [PersonaLab Memory Architecture](../ARCHITECTURE.md)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Configuration Guide](../CONFIG_GUIDE.md)

## 🤝 Contributing

Found an issue or want to improve the examples? Please check our [Contributing Guide](../CONTRIBUTING.md)! 