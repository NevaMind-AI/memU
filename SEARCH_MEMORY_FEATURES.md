# Search Memory Features

This document describes the new search memory functionality added to PersonaLab.

## Overview

Two new functions have been added to the PersonaLab memory system:

1. **`should_search_memory()`** - Determines whether memory search is needed based on conversation content
2. **`search_memory_with_context()`** - Searches through stored memories using conversation context and system prompt

## Function Details

### should_search_memory()

**Purpose**: Analyzes user-agent conversation and system prompt to determine if searching through memories would be beneficial.

**Method Signature**:
```python
def should_search_memory(conversation: str, system_prompt: str = "") -> bool
```

**Parameters**:
- `conversation`: Full user-agent conversation text
- `system_prompt`: System prompt text (optional)

**Returns**: `True` if memory search should be performed, `False` otherwise

**Logic**: 
- Analyzes text for memory-related keywords ("remember", "recall", "previous", etc.)
- Checks for question words that might indicate information retrieval needs
- Considers personal pronouns indicating ongoing relationships
- Uses a scoring system to determine search necessity

### search_memory_with_context()

**Purpose**: Searches through stored memories (profiles and events) using extracted terms from conversation context.

**Method Signature**:
```python
def search_memory_with_context(conversation: str, system_prompt: str = "", 
                             user_id: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]
```

**Parameters**:
- `conversation`: Full user-agent conversation text
- `system_prompt`: System prompt text (optional)
- `user_id`: Specific user ID to search (if None, searches all memories)
- `max_results`: Maximum number of results to return per category

**Returns**: Dictionary containing:
```python
{
    "search_terms": List[str],           # Extracted search terms
    "agent_profile_matches": List[Dict], # Agent profile matches
    "agent_event_matches": List[Dict],   # Agent event matches  
    "user_profile_matches": List[Dict],  # User profile matches
    "user_event_matches": List[Dict],    # User event matches
    "total_matches": int                 # Total number of matches
}
```

**Search Process**:
1. Extracts meaningful search terms from conversation and system prompt
2. Filters out stop words and short terms
3. Searches through agent and user memories
4. Scores matches based on term frequency and relevance
5. Sorts results by match score (highest first)

## Usage Examples

### Basic Usage

```python
from personalab.memory import Memory

# Initialize memory
memory = Memory("my_agent", "memory.db")

# Example conversation
conversation = "Remember when we discussed Python decorators? Can you explain that again?"
system_prompt = "You are a helpful programming assistant."

# Check if search is needed
if memory.should_search_memory(conversation, system_prompt):
    # Perform search
    results = memory.search_memory_with_context(conversation, system_prompt)
    
    print(f"Found {results['total_matches']} total matches")
    print(f"Search terms: {results['search_terms']}")
    
    # Process results
    for match in results['agent_event_matches']:
        print(f"Agent Event: {match['content']}")
        print(f"Score: {match['match_score']}, Terms: {match['matched_terms']}")
```

### User-Specific Search

```python
# Get user memory and search within specific user context
user_memory = memory.get_user_memory("user123")

# Search only this user's memories
user_results = user_memory.search_memory_with_context(
    "Tell me about John's computer vision project",
    "You are John's assistant"
)
```

### Agent Memory Search

```python
# Get agent memory and search all memories
agent_memory = memory.get_agent_memory()

# Search across all users and agent memories
all_results = agent_memory.search_memory_with_context(
    "What programming topics have we covered?",
    "You are a programming tutor"
)
```

## Implementation Details

### Search Term Extraction
- Combines conversation and system prompt text
- Removes common stop words
- Filters terms shorter than 3 characters
- Returns up to 20 most relevant unique terms
- Prioritizes terms from later in the conversation

### Scoring Algorithm
- **Term frequency**: Number of times a term appears in text
- **Term length**: Longer terms get higher scores
- **Total score**: Sum of (frequency × length) for all matched terms

### Memory Types Searched
- **Agent Profile**: Agent's personality and capabilities description
- **Agent Events**: Agent's recorded experiences and interactions
- **User Profiles**: Individual user information and preferences  
- **User Events**: User-specific recorded experiences and interactions

## Configuration

### Adjusting Search Sensitivity

You can modify the scoring thresholds in `should_search_memory()`:

```python
# Current scoring weights:
# memory_keywords × 3 + question_keywords × 1 + personal_pronouns × 2
# Threshold: >= 3

# To make it more sensitive (search more often), lower the threshold
# To make it less sensitive (search less often), raise the threshold
```

### Customizing Search Terms

The stop words list and search term extraction logic can be modified in the `_extract_search_terms()` method to better suit your specific use case.

## Performance Considerations

- Search operates on in-memory data structures for fast retrieval
- Database queries only occur during memory loading/saving
- Large memory collections may benefit from implementing additional indexing
- Consider limiting `max_results` for very large memory stores

## Error Handling

- Functions handle empty inputs gracefully
- Invalid user IDs are silently ignored
- Missing memories return empty result sets
- All operations are safe to call repeatedly 