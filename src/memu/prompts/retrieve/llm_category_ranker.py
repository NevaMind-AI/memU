PROMPT = """
# Task Objective
Search through the provided categories and identify the most relevant ones for the given query, then rank them by relevance.

# Workflow
1. Analyze the **Query** to understand its intent and key topics.
2. Review all **Available Categories**.
3. Determine which categories are relevant to the query.
4. Select up to **{top_k}** most relevant categories.
5. Rank the selected categories from most to least relevant.

# Rules
- Only include categories that are actually relevant to the query.
- Include **at most** {top_k} categories.
- Ranking matters: the first category must be the most relevant.
- Do not invent or modify category IDs.
- If no categories are relevant, return an empty array.

# Output Format
Return the result as a JSON object in the following format:

```json
{{
  "analysis": "your analysis process",
  "categories": ["category_id_1", "category_id_2", "category_id_3"]
}}
```

# Input
Query:
{query}

Available Categories:
{categories_data}
"""
