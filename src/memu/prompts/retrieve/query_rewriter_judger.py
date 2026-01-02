SYSTEM_PROMPT = """
# Task Objective
Perform two tasks:
1. **Query Rewriting** - Incorporate conversation context to make the query more specific and clear.
2. **Sufficiency Judgment** - Determine whether the retrieved content is sufficient to answer the query.

You should be conservative and only mark the result as **ENOUGH** when the retrieved content truly provides adequate information.

# Workflow
1. Review the **Query Context** to understand prior conversation and background.
2. Analyze the **Original Query**.
3. Examine the **Retrieved Content So Far**.
4. Rewrite the query by incorporating relevant context to improve clarity and specificity.
5. Judge whether the retrieved content is sufficient to answer the rewritten query based on defined criteria.

# Rules
- Query rewriting must stay faithful to the user's original intent.
- Only incorporate context that is relevant and helpful.
- Do not introduce new assumptions or external knowledge.
- Mark **ENOUGH** only if:
  - The retrieved content directly addresses the query, **and**
  - The information is specific and detailed enough, **and**
  - There are no obvious gaps or missing details.
- If any key information is missing or unclear, mark **MORE**.

# Output Format
Use the following structure:

<rewritten_query>
[Provide the rewritten query with conversation context]
</rewritten_query>

<judgement>
ENOUGH or MORE
</judgement>
"""

USER_PROMPT = """
Input:
Query Context:
{conversation_history}

Original Query:
{original_query}

Retrieved Content So Far:
{retrieved_content}
"""
