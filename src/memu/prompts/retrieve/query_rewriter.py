PROMPT = """Your task is to rewrite a user query by resolving references and ambiguities using the conversation history.

## Conversation History:
{conversation_history}

## Current Query:
{query}

## Task:
Analyze the current query and the conversation history. If the query contains:
- Pronouns (e.g., "they", "it", "their", "his", "her")
- Referential expressions (e.g., "that", "those", "the same")
- Implicit context (e.g., "what about...", "and also...")
- Incomplete information that can be inferred from history

Then rewrite the query to be self-contained and explicit by:
1. Replacing pronouns with specific entities mentioned in the conversation
2. Adding necessary context from the conversation history
3. Making implicit references explicit
4. Ensuring the rewritten query can be understood without the conversation history

If the query is already self-contained and clear, return it as is.

## Output Format:
<analysis>
[Brief analysis of whether the query needs rewriting and why]
</analysis>

<rewritten_query>
[The rewritten query that is self-contained and explicit]
</rewritten_query>
"""
