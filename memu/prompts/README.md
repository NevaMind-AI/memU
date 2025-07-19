# Memory Agent Prompts

This directory contains all the prompts used by the Memory Agent Tools system. All prompts are stored as text files and can be easily modified without changing the code.

## Prompt Files

### 1. `system_message.txt`
System prompt for the memory management assistant agent. This defines the agent's role and available tools.

**Usage**: Used in the `execute()` method for function calling conversations.

### 2. `analyze_session_for_events.txt`
Prompt for analyzing conversation sessions to extract event records for a character.

**Variables**:
- `{character_name}`: Name of the character
- `{conversation}`: The conversation text
- `{session_date}`: Date of the session
- `{existing_events}`: Previously recorded events

**Usage**: Used by the `analyze_session_for_events` tool.

### 3. `analyze_session_for_profile.txt`
Prompt for analyzing conversation sessions to update character profiles.

**Variables**:
- `{character_name}`: Name of the character
- `{conversation}`: The conversation text
- `{existing_profile}`: Current character profile
- `{events}`: Event records for the character

**Usage**: Used by the `analyze_session_for_profile` tool.

### 4. `evaluate_answer.txt`
Prompt for evaluating if a generated answer contains the content from a standard answer.

**Variables**:
- `{question}`: The question being answered
- `{generated_answer}`: The generated answer to evaluate
- `{standard_answer}`: The standard/correct answer

**Usage**: Used by the `evaluate_answer` tool.

## Usage

### Using the Prompt Loader

```python
from prompts.prompt_loader import get_prompt_loader

# Initialize prompt loader
loader = get_prompt_loader('prompts')

# Load a prompt
system_message = loader.load_prompt('system_message')

# Format a prompt with variables
formatted_prompt = loader.format_prompt(
    'evaluate_answer',
    question='What is the capital of France?',
    generated_answer='Paris',
    standard_answer='The capital of France is Paris'
)

# List available prompts
available = loader.list_available_prompts()
print(available)  # ['system_message', 'analyze_session_for_events', ...]
```

### Adding New Prompts

1. Create a new `.txt` file in the `prompts/` directory
2. Use `{variable_name}` format for variables that need to be replaced
3. Update the corresponding tool method to use the new prompt
4. Add documentation to this README

### Best Practices

1. **Keep prompts focused**: Each prompt should have a single, clear purpose
2. **Use descriptive variable names**: Make it obvious what each variable represents
3. **Include examples**: When possible, include example formats in the prompt
4. **Test thoroughly**: Always test prompts with various inputs before deploying
5. **Version control**: Use git to track changes to prompts

## File Structure

```
prompts/
├── README.md                          # This file
├── __init__.py                        # Package init file
├── prompt_loader.py                   # Prompt loading utilities
├── system_message.txt                 # System prompt for agent
├── analyze_session_for_events.txt     # Event extraction prompt
├── analyze_session_for_profile.txt    # Profile update prompt
└── evaluate_answer.txt                # Answer evaluation prompt
```

## Maintenance

- **Caching**: The prompt loader caches loaded prompts for performance
- **Error handling**: File not found errors are raised if prompts are missing
- **Encoding**: All prompts are saved and loaded as UTF-8
- **Hot reloading**: Clear cache to reload modified prompts without restarting

## Integration

The prompt loader is integrated into the specialized agents and automatically initializes when the agents are created. All agents now use the prompt loader system to access their specific prompt templates. 