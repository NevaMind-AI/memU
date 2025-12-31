PROMPT = """
# Task Objective
Search through the provided memory items and identify the most relevant ones for the given query, based on the already identified relevant categories, then rank them by relevance.

# Workflow
1. Analyze the **Query** to understand intent and key information needs.
2. Review the **Relevant Categories** provided to understand the scope.
3. Examine all **Available Memory Items** within those categories.
4. Identify which memory items are truly relevant to the query.
5. Select up to **top_k** most relevant items.
6. Rank the selected items from most to least relevant.

# Rules
- Only consider memory items that belong to the provided relevant categories.
- Only include items that are actually relevant to the query.
- Include **at most** {top_k} items.
- Order matters: the first item must be the most relevant.
- Do not invent, modify, or infer item IDs.
- If no relevant items are found, return an empty array.

# Output Format
Return the result as a JSON object in the following format:

```json
{{
  "analysis": "your analysis process",
  "items": ["item_id_1", "item_id_2", "item_id_3"]
}}
```

# Input
Query:
{query}

Available Memory Items:
{items_data}

These memory items belong to the following relevant categories that were already identified:
{relevant_categories}
"""
