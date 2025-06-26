# PersonaLab

[![PyPI version](https://badge.fury.io/py/personalab.svg)](https://badge.fury.io/py/personalab)
[![Python Version](https://img.shields.io/pypi/pyversions/personalab.svg)](https://pypi.org/project/personalab/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python framework for creating and managing AI personas and laboratory environments.

## Features

- ✨ Ultra-simple memory management for AI personas
- 🚀 Agent/User separation for different memory contexts
- 📦 String-based storage without complex categories

## Memory System

PersonaLab includes a hierarchical memory management system for AI personas:

### Architecture

```
Memory (Container)
├── AgentMemory
│   ├── ProfileMemory (string)
│   └── EventMemory (list)
└── UserMemory (per user)
    ├── ProfileMemory (string) 
    └── EventMemory (list)
```

### Memory Classes

- **Memory**: Main container that manages agent and user memories
- **AgentMemory**: Container for agent-specific profile and events
- **UserMemory**: Container for user-specific profile and events  
- **ProfileMemory**: Manages profiles as a single string
- **EventMemory**: Manages memories as timestamped strings

### Key Features

- **Hierarchical**: Clean separation between agent and user memories
- **Ultra-Simple**: ProfileMemory is just a string, EventMemory is just a list
- **Agent/User Separation**: One agent can handle multiple users
- **String-based Timestamps**: Human-readable datetime strings throughout  
- **No Categories**: No complex event types or metadata - just content and time
- **Easy API**: Intuitive hierarchical access patterns

### Usage Examples

```python
from personalab.memory import Memory

# Create main memory container
memory = Memory("chatbot_v1")

# Agent memory (profile + events)
agent = memory.get_agent_memory()
agent.profile.set_profile("System: ChatBot v1.0, Language: Chinese")
agent.events.add_memory("系统启动")

# User memory (profile + events) 
alice = memory.get_user_memory("alice")
alice.profile.set_profile("Name: Alice, Age: 25, Skill: Beginner")
alice.events.add_memory("用户询问天气信息")

# Simple retrieval
recent_memories = alice.events.get_recent_memories(5)
search_results = alice.events.search_memories("天气")
```

## Installation

### From PyPI (Recommended)

```bash
pip install personalab
```

### From Source

```bash
git clone https://github.com/NevaMind-AI/PersonaLab.git
cd PersonaLab
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/NevaMind-AI/PersonaLab.git
cd PersonaLab
pip install -e ".[dev]"
```

## Quick Start

```python
from personalab.memory import Memory

# Create memory container
memory = Memory("chatbot_v1")

# Setup agent
agent = memory.get_agent_memory()
agent.profile.set_profile("AI Assistant v1.0")
agent.events.add_memory("System started")

# Handle user
alice = memory.get_user_memory("alice")
alice.profile.set_profile("Name: Alice, Age: 25")
alice.events.add_memory("User asked about weather")
alice.events.add_memory("Provided weather information")

# Retrieve memories
recent = alice.events.get_recent_memories(2)
for mem in recent:
    print(mem)  # [2025-06-26 13:30:00] Provided weather information
```

## API Reference

### Memory

Main container that manages agent and user memories.

#### Methods

- `__init__(agent_id)` - Initialize memory for an agent
- `get_agent_memory()` - Get AgentMemory instance
- `get_user_memory(user_id)` - Get or create UserMemory for user
- `list_users()` - Get list of registered user IDs
- `get_memory_info()` - Get comprehensive memory information

### AgentMemory / UserMemory

Containers for agent/user-specific memories.

#### Properties

- `profile` - ProfileMemory instance (string storage)
- `events` - EventMemory instance (list storage)

### ProfileMemory

Manages profiles as a single string.

#### Methods

- `get_profile()` - Get the profile string
- `set_profile(profile_data)` - Set the profile string
- `clear()` - Clear the profile
- `get_size()` - Get length of profile string

### EventMemory

Manages memories as timestamped strings.

#### Methods

- `add_memory(content)` - Add a new memory
- `get_memories(limit=None)` - Get memories (recent first)
- `get_recent_memories(limit=10)` - Get recent memories  
- `search_memories(query, case_sensitive=False)` - Search memories by content
- `clear()` - Clear all memories
- `get_size()` - Get number of memories

## Development

### Setting up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/NevaMind-AI/PersonaLab.git
   cd PersonaLab
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Type Checking

```bash
mypy personalab
```

### Building the Package

```bash
python -m build
```

### Publishing to PyPI

```bash
python -m twine upload dist/*
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for details about changes in each version.

## Support

- 📧 Email: your.email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/NevaMind-AI/PersonaLab/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/NevaMind-AI/PersonaLab/discussions) 