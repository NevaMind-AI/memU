# MemU Memory Agent - Action-Based Architecture

Modern memory management system with **action-based architecture** for maximum modularity and maintainability.

## 🏗️ Architecture Overview

The new MemoryAgent uses an **action-based architecture** where each memory operation is implemented as a separate, independent module:

**Available Actions:**
- **add_memory**: Add new memory content  
- **read_memory**: Read memory content
- **search_memory**: Search memory using embeddings
- **update_memory**: Update specific memory item by ID
- **delete_memory**: Delete memory content
- **get_available_categories**: Get available categories

```
memory/
├── memory_agent.py        # Main agent orchestrator  
├── actions/               # Individual action modules
│   ├── __init__.py       # Action registry
│   ├── base_action.py    # Base class for all actions
│   ├── add_memory.py
│   ├── read_memory.py
│   ├── search_memory.py
│   ├── update_memory.py
│   ├── delete_memory.py
│   └── get_available_categories.py
└── embeddings/            # Per-line embedding storage
```

### 🎯 Key Benefits

- **Modularity**: Each function is a separate file
- **Maintainability**: Easy to modify individual operations
- **Extensibility**: Add new actions without touching core code
- **Testing**: Test each action independently
- **Function Calling**: Full OpenAI-compatible schemas

## 🚀 Quick Start

### Basic Usage

```python
from memu.memory import MemoryAgent
from memu.llm import YourLLMClient

# Initialize Memory Agent (action-based architecture)
memory_agent = MemoryAgent(
    llm_client=llm_client,
    memory_dir="memory",
    enable_embeddings=True
)

# Get available actions
actions = memory_agent.get_function_list()
print(f"Available actions: {actions}")
# Output: ['add_memory', 'read_memory', 'search_memory', 'update_memory', 'delete_memory', 'get_available_categories']
```

### Function Calling with LLM

```python
# 1. Get OpenAI-compatible function schemas
schemas = memory_agent.get_functions_schema()

# 2. Use with OpenAI API
import openai

response = openai.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Remember that I love cooking Italian food"}
    ],
    tools=[{"type": "function", "function": schema} for schema in schemas],
    tool_choice="auto"
)

# 3. Execute function calls from LLM response
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        # Execute the function call
        result = memory_agent.call_function(function_name, arguments)
        print(f"Action {function_name} result: {result}")
```

## 🔧 Available Actions

### 1. **add_memory** - Add new memory content
```python
result = memory_agent.call_function("add_memory", {
    "character_name": "Alice",
    "category": "profile", 
    "content": "Loves Italian cuisine and pasta making",
    "append": True,
    "generate_embeddings": True
})
```

### 2. **search_memory** - Semantic search across memories
```python
result = memory_agent.call_function("search_memory", {
    "character_name": "Alice",
    "query": "cooking preferences",
    "limit": 5,
    "use_embeddings": True
})
```

### 3. **read_memory** - Read specific or all memory categories
```python
# Read specific category
result = memory_agent.call_function("read_memory", {
    "character_name": "Alice",
    "category": "profile"
})

# Read all categories
result = memory_agent.call_function("read_memory", {
    "character_name": "Alice"
})
```

### 4. **update_memory** - Update specific memory item by ID
```python
result = memory_agent.call_function("update_memory", {
    "character_name": "Alice",
    "category": "profile",
    "memory_id": "a34a5f",  # ID of the memory item to update
    "new_content": "Updated profile information...",
    "regenerate_embeddings": True
})
# The old memory item is deleted and new content is added at the end with a new ID
```

### 5. **delete_memory** - Delete memory content
```python
# Delete specific category
result = memory_agent.call_function("delete_memory", {
    "character_name": "Alice",
    "category": "profile",
    "delete_embeddings": True
})

# Delete all memory for character
result = memory_agent.call_function("delete_memory", {
    "character_name": "Alice"
})
```

### 6. **get_available_categories** - Get all available categories
```python
result = memory_agent.call_function("get_available_categories", {})
```

## 🏗️ Action Architecture Details

### Base Action Class

All actions inherit from `BaseAction` which provides:

```python
from memu.memory.actions import BaseAction

class MyCustomAction(BaseAction):
    @property
    def action_name(self) -> str:
        return "my_custom_action"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible schema"""
        return {...}
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the action"""
        return {...}
```

### Memory Core

Shared functionality is provided by `MemoryCore`:
- LLM client access
- Storage manager
- Embedding client  
- Configuration
- Common utilities

### Action Registry

Actions are automatically registered in `actions/__init__.py`:

```python
from .actions import ACTION_REGISTRY

# Add new actions here
ACTION_REGISTRY["my_action"] = MyActionClass
```

## ⚡ **Advanced Features**

### **Per-Line Embeddings**
- Each line in markdown files is a separate memory item
- Individual embeddings for semantic search
- Incremental embedding updates

### **Dynamic Configuration**
- Memory categories loaded from config folders
- Customizable prompts per memory type
- Flexible file naming and organization

### **Semantic Search** 
- Vector-based similarity search
- Configurable similarity thresholds
- Fallback to text matching

### **Validation**: 
- Function call validation before execution
- Parameter type checking
- Error handling with detailed messages

### **High Performance**
- Async-ready architecture
- Efficient storage with JSON embeddings
- Minimal memory footprint

## 📁 File Structure

Memory is stored as markdown files with embeddings:

```
memory/
├── Alice_activity.md          # Activity records
├── Alice_profile.md           # Profile information  
├── Alice_event.md            # Important events
└── embeddings/
    └── Alice/
        ├── activity_embeddings.json
        ├── profile_embeddings.json
        └── event_embeddings.json
```

## 🛠 Adding Custom Actions

### 1. Create Action File

```python
# memu/memory/actions/my_action.py
from .base_action import BaseAction

class MyActionClass(BaseAction):
    @property
    def action_name(self) -> str:
        return "my_action"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "my_action",
            "description": "Does something cool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "First parameter"
                    }
                },
                "required": ["param1"]
            }
        }
    
    def execute(self, param1: str) -> Dict[str, Any]:
        try:
            # Your action logic here
            result = f"Processed: {param1}"
            
            return self._add_metadata({
                "success": True,
                "result": result,
                "message": "Action completed successfully"
            })
        except Exception as e:
            return self._handle_error(e)
```

### 2. Register Action

```python
# memu/memory/actions/__init__.py
from .my_action import MyActionClass

ACTION_REGISTRY = {
    # ... existing actions ...
    "my_action": MyActionClass
}
```

### 3. Use New Action

```python
result = memory_agent.call_function("my_action", {
    "param1": "test value"
})
```

## 🔍 Advanced Usage

### Custom Validation
```python
# Validate before calling
validation = memory_agent.validate_function_call("add_memory", {
    "character_name": "Alice",
    "category": "profile", 
    "content": "Some content"
})

if validation["valid"]:
    result = memory_agent.call_function("add_memory", arguments)
else:
    print(f"Validation failed: {validation['error']}")
```

### Direct Action Access
```python
# Get specific action instance for advanced usage
action = memory_agent.get_action_instance("search_memory")
if action:
    # Access action-specific methods
    schema = action.get_schema()
    result = action.execute(character_name="Alice", query="test")
```

### Batch Operations
```python
operations = [
    {"name": "add_memory", "args": {"character_name": "Alice", "category": "profile", "content": "Loves music"}},
    {"name": "search_memory", "args": {"character_name": "Alice", "query": "music"}},
    {"name": "read_memory", "args": {"character_name": "Alice", "category": "profile"}}
]

results = []
for op in operations:
    result = memory_agent.call_function(op["name"], op["args"])
    results.append(result)
```

## 🚀 Performance & Scalability

- **Modular Design**: Independent actions for better maintainability
- **Lazy Loading**: Actions loaded on demand
- **Memory Efficient**: Shared core resources
- **Embedding Optimization**: Per-line incremental updates
- **Error Isolation**: Action failures don't affect others

This action-based architecture provides maximum flexibility while maintaining the simple function calling interface that LLMs expect. 