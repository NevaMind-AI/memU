# Persona Feature Options

PersonaLab's Persona class provides flexible feature options, allowing you to selectively enable different functionalities based on your needs.

## Core Parameters

### `use_memory` (bool, default: True)
Controls whether to enable long-term memory functionality.

**When enabled, includes:**
- Fact memory (Facts)
- User preferences (Preferences)
- Important events (Events)
- Psychological model (Theory of Mind)

**Suitable scenarios:**
- ✅ Personalized AI assistants
- ✅ Long-term user relationship building
- ✅ Smart recommendation systems
- ❌ Anonymous short-term interactions
- ❌ Privacy-sensitive scenarios

### `use_memo` (bool, default: True)
Controls whether to enable conversation recording and retrieval functionality.

**When enabled, includes:**
- Conversation history recording
- Semantic vector search
- Relevant conversation retrieval
- Context enhancement

**Suitable scenarios:**
- ✅ Complex multi-turn conversations
- ✅ Customer service systems
- ✅ Knowledge Q&A
- ❌ Simple single-turn conversations
- ❌ Low-latency requirements

## Usage Patterns

### Full Features (Recommended)
```python
from personalab import Persona

persona = Persona(
    agent_id="assistant",
    use_memory=True,
    use_memo=True
)
```

### Memory Only
```python
persona = Persona(
    agent_id="assistant", 
    use_memory=True,
    use_memo=False
)
```
- 💡 Suitable for: Personal assistants that don't need historical conversation retrieval
- ⚡ Advantages: Faster response, lower storage requirements
- ⚠️ Limitations: Cannot reference historical conversation content

### Retrieval Only
```python
persona = Persona(
    agent_id="assistant",
    use_memory=False, 
    use_memo=True
)
```
- 💡 Suitable for: Customer service systems, knowledge base Q&A
- ⚡ Advantages: Powerful retrieval capabilities without storing personal information
- ⚠️ Limitations: Won't form long-term understanding of users

### Minimal Functionality
```python
persona = Persona(
    agent_id="assistant",
    use_memory=False,
    use_memo=False
)
```
- 💡 Suitable for: Pure LLM conversation, anonymous interactions
- ⚡ Advantages: Fastest response, lowest storage
- ⚠️ Limitations: No memory functionality

## Performance Comparison

| Feature Combination | Response Speed | Storage Requirements | Personalization Level | Context Understanding |
|---------------------|----------------|---------------------|----------------------|----------------------|
| Full Features | Slower | High | 🌟🌟🌟🌟🌟 | 🌟🌟🌟🌟🌟 |
| Memory Only | Medium | Medium | 🌟🌟🌟🌟 | 🌟🌟 |
| Memo Only | Medium | Medium | 🌟 | 🌟🌟🌟🌟 |
| Minimal | Fastest | Lowest | None | 🌟 |

## Dynamic Control

You can control memory update behavior through the learn parameter:

```python
# Don't update memory for this conversation
response = persona.chat("temporary question", learn=False)

# Normal memory update (default) - record conversation to events
response = persona.chat("important information", learn=True)
```

### Memory Update Mechanism

When `learn=True` (default), Persona will:
- **Memo functionality**: Record conversation to conversation history, supporting subsequent retrieval
- **Memory functionality**: Add complete conversation as an event to event memory

This is a simplified memory mechanism that directly stores conversation content as events, facilitating quick recording and retrieval.

## Error Handling

When features are not enabled, related methods handle gracefully:

```python
# When use_memory=False
persona.add_memory("fact")  # Shows: ⚠️ Memory functionality is not enabled
persona.get_memory()        # Returns: {"facts": [], ...}

# When use_memo=False  
persona.search("query")     # Shows: ⚠️ Memo functionality is not enabled
                           # Returns: []
```

## Recommended Configurations

### Personal AI Assistant
```python
persona = Persona(agent_id="personal_ai", use_memory=True, use_memo=True)
```

### Enterprise Customer Service
```python  
persona = Persona(agent_id="customer_service", use_memory=False, use_memo=True)
```

### Anonymous Q&A
```python
persona = Persona(agent_id="qa_bot", use_memory=False, use_memo=False)
```

### Educational Assistant
```python
persona = Persona(agent_id="tutor", use_memory=True, use_memo=True, show_retrieval=True)
``` 