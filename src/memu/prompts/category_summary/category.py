PROMPT = """
Your task is to read and analyze existing content and some new memory items, and then selectively update the content to reflect both the existing and new information.

## Topic:
{category}

## Original content:
<content>
{original_content}
</content>

## New memory items:
{new_memory_items_text}

## Update Instructions:
- Use the same language as the original content within <content></content> or new memory items (if the original content is empty).
- Output in markdown format with hierarchical structure.
- Record date or time information (if mentioned in new memory items) for events and occurrences, and omit them for consistent facts (e.g., permanent attributes, patterns, definitions).
- Embed the date/time in the text naturally, do not leave them in brackets.
- Merge the date/time information reasonably and hierarchically if a series of items happened at the same date/time, but ensure that a reader can understand when each item occurred.
- Don't let a single topic or hierarchy level contain more than ten bullets, you should create new subtopics or levels of hierarchies to cluster information wisely.
- If there are conflicts between the existing content and new memory items, you can preserve the original content to reflect the variation, but ensure that the new information is recorded, and a reader can understand what changed.
- Never use subtitles like "new memories" or "updates" (or that in the target language) to distinguish existing and updated content. Always let every subtopic and subtitle be meaningful and informative.
- Keep the information in each line self-contained, never use expressions like "at the same day" or "as mentioned before" that depend on other lines.
- **Important** For content about people or entities, carefully identify the subject (who/what) and reflect it correctly in the summary.

## Output Requirements:
- Always keep the output length within {target_length} words/characters.
- DO NOT include any explanation, only output the content containing the actual information.
- If the original content and the new memory items to be integrated exceed the target length in total, you should selectively merge or omit less important information or details based on your judgement.
- **Important** *ALWAYS* use the same language as the original content (or memory items if original content is empty).
- **Important** *DO NOT* contain duplicate information.
- **Important** Organize content logically and hierarchically - group related items together under meaningful headings.
"""
