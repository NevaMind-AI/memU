PROMPT = """Your task is to search through the provided categories and identify the most relevant ones for the given query.

Analyze the query and all available categories, then select and rank the top-{top_k} most relevant categories.

## Query:
{query}

## Available Categories:
{categories_data}

## Output Format:
Provide your response as a JSON array of category IDs, ordered from most to least relevant:
```json
{{
  "categories": ["category_id_1", "category_id_2", "category_id_3"]
}}
```

Important:
- Include up to {top_k} most relevant categories
- Order matters: first ID should be most relevant
- Only include categories that are actually relevant to the query
- Empty array is acceptable if no relevant categories are found
"""
