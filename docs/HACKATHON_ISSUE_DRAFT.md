# GitHub Issue Draft: Memory Types + Tool Memory

## Title
`[2026NewYearChallenge] Specialized Memory Types with Tool Learning`

---

## Description

### What will this task implement?

This PR enhances MemU's memory type system to support specialized memory structures with type-specific metadata and introduces Tool Memory for agent self-improvement.

**Current State:** MemU has a `memory_type` field with 5 types (profile, event, knowledge, behavior, skill) and uses different LLM prompts to extract each type. However, after extraction, all memories share the same storage schema - just `summary` and `embedding`. There's no type-specific metadata, no type-aware retrieval, and no way for agents to learn from their tool usage.

**Enhancement:** Extend the memory system to support:
- Type-specific metadata fields (e.g., `when_to_use` for smarter retrieval)
- Tool Memory type for tracking tool execution history
- Tool usage statistics for agent self-improvement
- Type-aware retrieval filtering

**Key Benefits:**
- Agents can learn from their own tool usage patterns
- Smarter retrieval based on memory context
- Foundation for agents that improve over time
- Better alignment with agentic application needs

---

## Requirements

- [x] Type-specific metadata schema with `when_to_use` field
- [x] Tool Memory implementation with execution tracking
- [x] Tool statistics (success_rate, avg_time_cost, avg_score)
- [ ] Type-aware retrieval filtering
- [x] Tests for Tool Memory CRUD and statistics
- [ ] Documentation and usage examples

---

## Review Criteria

- Correctness: All tests pass, no regressions
- Quality: Clean code, follows existing patterns
- DX: Clear documentation and examples
- Impact: Enables agent self-improvement use cases

---

## Implementation Summary

### Files Modified:
1. `src/memu/database/models.py` - Added `ToolCallResult` model, extended `MemoryItem` with `when_to_use`, `metadata`, `tool_calls` fields
2. `src/memu/database/repositories/memory_item.py` - Updated interface with new fields
3. `src/memu/database/inmemory/repositories/memory_item_repo.py` - Updated implementation
4. `src/memu/database/postgres/repositories/memory_item_repo.py` - Updated implementation
5. `src/memu/database/postgres/models.py` - Added JSON columns for new fields
6. `src/memu/prompts/memory_type/__init__.py` - Added tool type
7. `src/memu/prompts/memory_type/tool.py` - New prompt for tool memory extraction

### Files Added:
1. `tests/test_tool_memory.py` - 14 unit tests for Tool Memory feature

---

## Notes

This builds on MemU's existing memory type foundation while adding the specialized structures needed for agentic applications. The Tool Memory feature is particularly valuable for agents that need to learn which tools work best in different situations.
