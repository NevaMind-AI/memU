Closes #252

## What this PR does

Adds an OpenAgents adapter that enables any agent in an OpenAgents network to use MemU for long-term memory.

**Track:** A - Agent Framework Plugins/Adapters (5 points)

## The Problem

OpenAgents agents are stateless by default. When an agent restarts or a conversation ends, all context is lost.

## The Solution

A plug-and-play adapter:

```python
from memu.adapters.openagents import MemUOpenAgentsAdapter

adapter = MemUOpenAgentsAdapter(service=memu_service)
tools = adapter.get_tools()  # Ready for agent registration
```

Or via YAML config:
```yaml
tools:
  - name: "memorize"
    implementation: "memu.adapters.openagents.tools.memorize"
```

## Tools Provided

| Tool | Description |
|------|-------------|
| `memorize` | Store memories from text, conversations, documents |
| `retrieve` | Semantic search over memories |
| `list_memories` | List stored memory items |
| `get_memory` | Get specific memory by ID |

## Files Added

- `src/memu/adapters/__init__.py`
- `src/memu/adapters/openagents/__init__.py`
- `src/memu/adapters/openagents/adapter.py`
- `src/memu/adapters/openagents/tools.py`
- `src/memu/adapters/openagents/README.md`
- `examples/openagents/memory_agent.yaml`
- `examples/openagents/demo.py`
- `examples/openagents/infra_genius_integration.py`
- `tests/test_openagents_adapter.py` (20 tests)
- `tests/test_openagents_integration.py` (15 tests)

## Tests

All 35 tests passing.

## Dependencies

- Works standalone with core MemU
- Enhanced with Knowledge Graph (#249) for relationship traversal
- Enhanced with Tool Memory (#247) for success rate tracking
- Enhanced with Memory Reasoning (#251) for inference
