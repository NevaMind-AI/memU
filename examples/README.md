# PersonaLab Chat Examples

This directory contains examples demonstrating how to use PersonaLab's Persona chat functionality.

## Setup

### 1. Prerequisites

- Python 3.8+
- PostgreSQL database (for memory storage)
- OpenAI API key

### 2. Installation

```bash
# Install PersonaLab with AI dependencies
pip install personalab[ai]

# Or install from source (if in development)
pip install -e .[ai]
```

### 3. Environment Configuration

Copy the `.env.example` file to `.env` and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=personalab

# Optional: Logging
LOG_LEVEL=INFO
```

## Examples

### 🚀 Quick Start (`quick_start_chat.py`)

**Best for:** First-time users who want to see PersonaLab in action quickly.

A minimal example showing:
- Basic persona creation
- Simple chat conversation
- Memory functionality with retrieval indicators
- Proper cleanup

```bash
python examples/quick_start_chat.py
```

**Output Preview:**
```
🚀 PersonaLab Quick Start Chat
========================================
✅ AI Assistant created!
💬 Starting conversation...
----------------------------------------

👤 User: Hi! What can you help me with?
🤖 Assistant: Hello! I'm here to help you with a wide variety of tasks...

👤 User: Can you remember what I told you about learning Python?
🔍 [PersonaLab is searching memory for relevant context...]
🤖 Assistant: Yes, I remember you mentioned you're learning Python programming...
```

### 💬 Interactive Chat (`interactive_chat.py`)

**Best for:** Users who want to experience PersonaLab's memory retrieval in real-time.

An interactive chat interface featuring:
- Real-time conversation with memory retrieval visualization
- Commands to check memory state (`memory`)
- Ability to clear conversation history (`clear`)
- Live demonstration of context retrieval

```bash
python examples/interactive_chat.py
```

**Features:**
- `exit` or `quit` - End conversation and save memory
- `memory` - View current memory state
- `clear` - Start fresh conversation
- `🔍` indicators show when memory is being retrieved

**Example Session:**
```
🤖 PersonaLab Interactive Chat with Memory Retrieval
============================================================
💬 Type 'exit' or 'quit' to end the conversation
📝 Type 'memory' to see what the AI remembers about you
🔄 Type 'clear' to start a fresh conversation
🔍 Watch for retrieval indicators during the conversation!
============================================================

👤 You: Hi, I'm Sarah and I love photography
🤖 Assistant: Hello Sarah! It's wonderful to meet you...

👤 You: What camera gear would you recommend?
🔍 [Checking memory for relevant context...]
🤖 Assistant: Based on your interest in photography, Sarah...
```

### 🤖 Full Feature Demo (`persona_chat_example.py`)

**Best for:** Developers who want to understand all PersonaLab capabilities.

A comprehensive example demonstrating:
- Advanced persona configuration
- Memory persistence across sessions
- **Memory retrieval visualization** - see when PersonaLab searches memory
- Multi-user conversation isolation
- Session management
- Historical context retrieval

```bash
python examples/persona_chat_example.py
```

**Features Demonstrated:**

1. **Basic Chat** - Simple back-and-forth conversation
2. **Memory Management** - AI remembers user information across sessions
3. **🔍 Memory Retrieval** - Visual demonstration of context search
4. **Multi-User Support** - Multiple users with isolated memories
5. **Session Management** - Organized conversation sessions
6. **Resource Cleanup** - Proper shutdown procedures

## Key Concepts

### 🧠 Memory System

PersonaLab automatically manages long-term memory:

```python
# Enable memory when creating persona
persona = Persona(
    agent_id="my_ai",
    personality="Your AI personality...",
    use_memory=True,  # Enable long-term memory
    show_retrieval=True  # Show retrieval process
)

# Chat with memory context
response = persona.chat("Hello!", user_id="user_123")

# End session to update memory
persona.endsession("user_123")

# Retrieve memory information
memory = persona.memory_client.get_memory_by_agent(persona.agent_id, "user_123")
```

### 🔍 Retrieval Visualization

See when PersonaLab searches memory:

```python
persona = Persona(
    agent_id="my_ai",
    show_retrieval=True,  # Show when memory is retrieved
    use_memory=True       # Enable memory functionality
)

# During chat, you'll see indicators like:
# 🔍 [PersonaLab is searching memory for relevant context...]
# ✅ [Memory context used in response]
```

### 👥 Multi-User Isolation

Each user has their own memory space:

```python
# User A's conversation
persona.chat("I like Python", user_id="alice")

# User B's conversation (isolated from Alice)
persona.chat("I prefer JavaScript", user_id="bob")

# Each user has separate memory
alice_memory = persona.memory_client.get_memory_by_agent(persona.agent_id, "alice")
bob_memory = persona.memory_client.get_memory_by_agent(persona.agent_id, "bob")
```

### 🎭 Personality Configuration

Define your AI's behavior:

```python
persona = Persona(
    agent_id="tutor",
    personality="""You are a patient programming tutor who:
    - Explains concepts clearly
    - Asks follow-up questions
    - Encourages students
    - Adapts to different learning styles""",
    use_memory=True
)
```

## Troubleshooting

### Common Issues

**"OPENAI_API_KEY not found"**
- Ensure your `.env` file contains `OPENAI_API_KEY=your_key_here`
- Or set the environment variable: `export OPENAI_API_KEY=your_key_here`

**"Database connection failed"**
- Check your PostgreSQL database is running
- Verify database credentials in `.env`
- Ensure the database exists and is accessible

**"Module not found"**
- Install PersonaLab: `pip install personalab[ai]`
- If developing locally: `pip install -e .[ai]`

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in `.env`:
```env
LOG_LEVEL=DEBUG
```

## Next Steps

After running these examples:

1. **Integrate into your application** - Use PersonaLab in your own projects
2. **Customize personalities** - Create domain-specific AI assistants
3. **Explore advanced features** - Check the full PersonaLab documentation
4. **Join the community** - Contribute to PersonaLab development

## API Reference

### Core Methods

```python
# Create persona
persona = Persona(agent_id, personality, use_memory=True, show_retrieval=True)

# Chat
response = persona.chat(message, user_id)

# End session (saves memory)
persona.endsession(user_id)

# Get memory
memory = persona.memory_client.get_memory_by_agent(persona.agent_id, user_id)

# Cleanup
persona.close()
```

### Memory Structure

```python
memory = {
    'profile': 'User profile summary...',
    'events': ['Event 1', 'Event 2', ...],
    'mind': ['AI insight 1', 'AI insight 2', ...]
}
```

### Retrieval Parameters

```python
persona = Persona(
    show_retrieval=True,         # Show retrieval indicators
    use_memory=True,             # Enable memory functionality
    timeout=30                   # API request timeout in seconds
)
```

## Support

- 📖 **Documentation**: Check the main PersonaLab docs
- 🐛 **Issues**: Report bugs in the GitHub repository
- 💬 **Community**: Join our Discord/Slack for discussions 