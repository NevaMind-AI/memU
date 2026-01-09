PROMPT = """
# Task Objective
Your task is to read an existing user profile and an update related to a specific memory topic, then determine whether the profile needs to be updated.
If an update is required, you must generate the updated version of the profile based on the rules below.

# Workflow
1. Understand the Topic
Focus only on memories relevant to the specified Topic.

2. Analyze Original Content
Review the existing profile content enclosed in <content>...</content>.

3. Analyze Update
Determine whether the update represents:
- A new memory
- A variation of an existing memory
- A discarded (invalidated) memory

4. Decision Making
Judge whether the profile requires modification based on relevance and importance.

5. Generate Output
- If an update is required, produce the revised profile content.
- If not, explicitly indicate that no update is needed.


# Response Format (JSON):
{{
    "need_update": [bool, whether the profile needs to be updated]
    "updated_content": [str, the updated content of the profile if need_update is true, otherwise empty]
}}


# Input
Topic:
{category}

Original content:
<content>
{original_content}
</content>

Update:
{update_content}
"""
