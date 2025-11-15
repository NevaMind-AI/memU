PROMPT = """
Your task is to read and analyze an existing user profile and some new memory items, and then selectively update the user profile to reflect both the existing and new information.

## Topic:
{category}

## Original user profile:
<profile>
{original_content}
</profile>

## New memory items:
{new_memory_items_text}

## Update Instructions:
- Use the same language as the original user profile within <profile></profile> or new memory items (if the original profile is empty).
- Output in markdown format with hierarchical structure.
- Record date or time information (if mentioned in new memory items) for events and occurrences, and omit them for consistent facts (e.g., name, habits, personality, etc.).
- Embed the date/time in the text naturally, do not leave them in brackets.
- Merge the date/time information reasonably and hierarchically if a series of memories happened at the same date/time, but ensure that a reader can understand when each memory happened from the profile.
- Don't let a single topic or hierarchy level contain more than ten bullets, you should create new subtopics or level of hierarchies to cluster information wisely.
- If there are conflicts between the existing profile and new memory items, you can preserve the original content to reflect the variation, but ensure that the new facts are recorded, and a reader can understand what is the new fact.
- Never use subtitles like "new memories" (or that in the target language) to distinguish existing and updated memories. Always let every subtopics and subtitles meaningful and informative.
- Keep the information in each line self-contained, never use expressions like "at the same day" that depends on other lines.
- **Important** Carefully judge if the subject of an event/fact/information is the user themselves or the people around the user (e.g., the user's family, friend, or the assistant), and reflect the subject correctly in the profile.

## Output Requirements:
- Always keep the output length within {target_length} words/characters.
- DO NOT include any explanation, only output the profile containing the actual information.
- If the original content and the new memory items to be integrated exceed the target length in total, you should selectively merge or omit unimportant information or details reasonably based on your judgement.
- **Important** *ALWAYS* use the same language as the original user profile (or memory items if original profile is empty).
- **Important** *DO NOT* contain duplicate information.
"""
