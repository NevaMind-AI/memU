PROMPT = """Your task is to search through the provided resources and identify the most relevant ones for the given query.

These resources are related to the following categories and items that were already identified:
{context_info}

Analyze the query and the available resources, then select and rank the top-{top_k} most relevant resources.

## Query:
{query}

## Available Resources:
{resources_data}

## Output Format:
Provide your response as a JSON array of resource IDs, ordered from most to least relevant:
```json
{{
  "resources": ["resource_id_1", "resource_id_2", "resource_id_3"]
}}
```

Important:
- Include up to {top_k} most relevant resources
- Order matters: first ID should be most relevant
- Only include resources that are actually relevant to the query
- Empty array is acceptable if no relevant resources are found
"""
