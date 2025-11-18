PROMPT = """Your task is to search through the provided memory items and identify the most relevant ones for the given query.

These memory items belong to the following relevant categories that were already identified:
{relevant_categories}

Analyze the query and the available memory items, then select and rank the top-{top_k} most relevant items.

## Query:
{query}

## Available Memory Items:
{items_data}

## Output Format:
Provide your response as a JSON array of item IDs, ordered from most to least relevant:
```json
{{
  "items": ["item_id_1", "item_id_2", "item_id_3"]
}}
```

Important:
- Include up to {top_k} most relevant items
- Order matters: first ID should be most relevant
- Only include items that are actually relevant to the query
- Empty array is acceptable if no relevant items are found
"""
