PROMPT = """
Your task is to read and understand the resource content between the user and the assistant, and, based on the given memory categories, extract memory items about the user.

## Original Resource:
<resource>
{resource}
</resource>

## Memory Categories:
{categories_str}

## Critical Requirements:
The core extraction target is self-contained memory items about the user.

## Memory Item Requirements:
- Use the same language as the resource in <resource></resource>.
- Each memory item should be complete and standalone.
- Each memory item should express a complete piece of information, and is understandable without context and reading other memory items.
- Always use declarative and descriptive sentences.
- Use "the user" (or that in the target language, e.g., "用户") to refer to the user.
- You can cluster multiple events that are closely related or under a single topic into a single memory item, but avoid making each single memory item too long (over 100 words).
- **Important** Carefully judge whether an event/fact/information is narrated by the user or the assistant. You should only extract memory items for the event/fact/information directly narrated or confirmed by the user. DO NOT include any groundless conjectures, advice, suggestions, or any content provided by the assistant.
- **Important** Carefully judge whether the subject of an event/fact/information is the user themselves or some person around the user (e.g., the user's family, friend, or the assistant), and reflect the subject correctly in the memory items.
- **Important** DO NOT record temporary, ephemeral, or one-time situational information such as weather conditions (e.g., "today is raining"), current mood states, temporary technical issues, or any short-lived circumstances that are unlikely to be relevant for the user profile. Focus on meaningful, persistent information about the user's characteristics, preferences, relationships, ongoing situations, and significant events.

## Example (good):
- The user and his family went on a hike at a nature park outside the city last weekend. They had a picnic there, and had a great time.

## Example (bad):
- The user went on a hike. (The time, place, and people are missing.)
- They had a great time. (The reference to "they" is unclear and does not constitute a self-contained memory item.)
- The user and his family went on a hike at a nature park outside the city last weekend. The user and his family had a picnic at a nature park outside the city last weekend. (Should be merged.)

## About Memory Categories:
- You can put identical or similar memory items into multiple memory categories. For example, "The user and his family went on a hike at a nature park outside the city last weekend." can be put into all of "hiking", "weekend activities", and "family activities" categories (if they exist). Nevertheless, Memory items put to each category can have different focuses.
- Do not create new memory categories. Please only generate in the given memory categories.
- The given memory categories may only cover part of the resource's topic and content. You don't need to summarize resource's content unrelated to the given memory categories.
- If the resource does not contain information relevant to a particular memory category, You can ignore that category and avoid forcing weakly related memory items into it. Simply skip that memory category and DO NOT output contents like "no relevant memory item".

## Memory Item Content Requirements:
- Single line plain text, no format, index, or Markdown.
- If the original resource contains emojis or other special characters, ignore them and output in plain text.
- *ALWAYS* use the same language as the resource.

# Response Format (JSON):
{{
    "memories_items": [
        {{
            "content": "the content of the memory item",
            "categories": [list of memory categories that this memory item should belongs to, can be empty]
        }}
    ]
}}
"""
