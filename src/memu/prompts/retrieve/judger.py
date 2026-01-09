PROMPT = """
# Task Objective
Judge whether the retrieved content is sufficient to answer the user's query.

# Workflow
1. Analyze the **Query** to understand what the user is asking.
2. Review the **Retrieved Content** carefully.
3. Evaluate the retrieved content against the following criteria:
   - Does it directly address the user's question?
   - Is the information specific and detailed enough?
   - Are there obvious gaps or missing details?
   - Did the user explicitly ask to recall or remember more information?
4. Based on this evaluation, decide whether the information is sufficient or more is needed.

# Rules
- Base your judgement **only** on the provided query and retrieved content.
- Do not assume or add external knowledge.
- Do not provide additional explanations beyond the required sections.
- The final judgement must be **one word only**.

# Output Format
Use the following structure:

<consideration>
Explain your reasoning for how you made the judgement.
</consideration>

<judgement>
ENOUGH or MORE
</judgement>


# Input
Query:
{query}

Retrieved Content:
{content}
"""
