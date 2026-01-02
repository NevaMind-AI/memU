PROMPT = """
# Task Objective
Rewrite a user query to make it self-contained and explicit by resolving references and ambiguities using the conversation history.

# Workflow
1. Review the **Conversation History** to identify relevant entities, topics, and context.
2. Analyze the **Current Query**.
3. Determine whether the query contains:
   - Pronouns (e.g., “they”, “it”, “their”, “his”, “her”)
   - Referential expressions (e.g., “that”, “those”, “the same”)
   - Implicit context (e.g., “what about…”, “and also…”)
   - Incomplete information that can be inferred from the conversation history
4. If rewriting is needed:
   - Replace pronouns with specific entities mentioned in the conversation
   - Add necessary background from the conversation history
   - Make implicit references explicit
   - Ensure the rewritten query is understandable on its own
5. If the query is already clear and self-contained, keep it unchanged.

# Rules
- Preserve the original intent of the user query.
- Only use information explicitly available in the conversation history.
- Do not introduce new assumptions or external knowledge.
- Keep the rewritten query concise but fully explicit.

# Output Format
Use the following structure:

<analysis>
Brief analysis of whether the query needs rewriting and why.
</analysis>

<rewritten_query>
The rewritten query that is self-contained and explicit if no rewrite is needed).
</rewritten_query>


# Input
Query Context:
{conversation_history}

Current Query:
{query}
"""
