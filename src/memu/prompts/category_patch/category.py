PROMPT = """
Your task is to read an existing user profile and an update about an specific memory, and then judge whether the profile need to be updated, and if so, generate the updated profile.

## Topic:
{category}

## Original content:
<content>
{original_content}
</content>

## Update:
{update_content}

## Update Instructions:
- If the update indicates that a new memory emerges, you should judge whether it is related to the topic, and if so, you should update the profile.
- If the update indicates that a memory varies, you should judge whether the original information is contained in the profile. It's possible that the original information is not mentioned in the profile if it's less important or less relevant to the topic, if so, you don't need to update the profile. Or, you should update the profile to reflect the new information.
- If the update indicates that a memory is discarded, you should judge whether the original information is contained in the profile. If so, you should update the profile to remove the corresponding information.
- If the updated profile is empty, return a textual "empty" instead of an empty string.

# Response Format (JSON):
{{
    "need_update": [bool, whether the profile needs to be updated]
    "updated_content": [str, the updated content of the profile if need_update is true, otherwise empty]
}}
"""
