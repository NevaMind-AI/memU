SYSTEM_PROMPT = """
# Task Objective
Determine whether the current query requires retrieving information from memory or can be answered directly without retrieval.
If retrieval is required, rewrite the query to include relevant contextual information.

# Workflow
1. Review the **Query Context** to understand prior conversation and available background.
2. Analyze the **Current Query**.
3. Consider the **Retrieved Content**, if any.
4. Decide whether memory retrieval is required based on the criteria.
5. If retrieval is needed, rewrite the query to incorporate relevant context from the query context.
6. If retrieval is not needed, keep the original query unchanged.

# Rules
- **NO_RETRIEVE** for:
  - Greetings, casual chat, or acknowledgments
  - Questions about only the current conversation/context
  - General knowledge questions
  - Requests for clarification
  - Meta-questions about the system itself
- **RETRIEVE** for:
  - Questions about past events, conversations, or interactions
  - Queries about user preferences, habits, or characteristics
  - Requests to recall specific information
  - Questions referencing historical data
- Do not add external knowledge beyond the provided context.
- If retrieval is not required, return the original query exactly.

# Output Format
Use the following structure:

<decision>
RETRIEVE or NO_RETRIEVE
</decision>

<rewritten_query>
If RETRIEVE: provide a rewritten query incorporating relevant context.
If NO_RETRIEVE: return `{query}` unchanged.
</rewritten_query>
"""


USER_PROMPT = """
# Input
Query Context:
{conversation_history}

Current Query:
{query}

Retrieved Content:
{retrieved_content}
"""
