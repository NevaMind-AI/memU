# Appendix: Minimal Memory Policy (memU-style)

## A. Memory Write Decision

def should_create_memory_item(resource: Resource, item: MemoryItem) -> bool:
    if item.is_emotional() and not item.is_recurrent():
        return False
    if item.is_hypothetical():
        return False
    if item.is_context_bound():
        return False
    if item.is_explicit_preference():
        return True
    if item.is_recurrent() and item.affects_planning():
        return True
    return False


## B. Memory Update Strategy

def resolve_memory_item_update(
    existing: MemoryItem,
    incoming: MemoryItem
) -> MemoryItem:
    if incoming.explicitly_negates(existing):
        return existing.overwrite_with(incoming)
    if incoming.conflicts_with(existing):
        return existing.coexist_with(incoming)
    return existing.consolidate_with(incoming)


## C. Category-Level Consolidation (Optional)

def consolidate_category(category: MemoryCategory) -> MemoryCategory:
    if category.should_consolidate():
        return category.summarize_items()
    return category


## D. Retrieval Guardrail

def should_use_memory_item(item: MemoryItem, current_task) -> bool:
    if not item.is_relevant_to(current_task):
        return False
    if item.is_low_confidence() and item.is_outdated():
        return False
    return True
