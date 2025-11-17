PROMPT = """Your task is to judge if the retrieved results are enough to answer the query.

Analyze the query and the retrieved content, and consider the following criteria:
1. Does the retrieved content directly address the user's question?
2. Is the information specific and detailed enough?
3. Are there any obvious gaps or missing details?
4. Did the user explicitly ask to recall or remember more information?

Then, give your final judgement with ONLY ONE WORD:
- "ENOUGH" if the retrieved content provides adequate information to answer the query
- "MORE" if additional information is needed to properly answer the query

## Query:
{query}

## Retrieved Content:
{content}

## Output Format:
<consideration>
[Explain your consideration for how you make the judgement]
</consideration>

<judgement>
[Your judgement: "ENOUGH" or "MORE"]
</judgement>
"""
