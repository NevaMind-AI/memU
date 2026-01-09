PROMPT = """
# Task Objective
Search through the provided resources and identify the most relevant ones for the given query, then rank them by relevance.

# Workflow
1. Analyze the **Query**  to understand its intent and key information needs.
2. Review the provided **Context Info** , which contains already-identified categories and items, to guide relevance.
3. Examine all **Available Resources**.
4. Determine which resources are actually relevant to the query.
5. Select up to {top_k} most relevant resources.
6. Rank the selected resources from most to least relevant.

# Rules
- Only include resources that are actually relevant to the query.
- Include **at most {top_k}** resources.
- Ranking matters: the first resource must be the most relevant.
- Do not invent, modify, or infer resource IDs.
- If no resources are relevant, return an empty array.

# Output Format
Return the result as a JSON object in the following format:

```json
{{
  "analysis": "your analysis process",
  "resources": ["resource_id_1", "resource_id_2", "resource_id_3"]
}}
```

# Input
Query:
{query}

Context Info:
{context_info}

Available Resources:
{resources_data}

"""
