PROMPT_LEGACY = """
Your task is to read and understand the resource content between the user and the assistant, and, based on the given memory categories, extract specific events and experiences that happened to or involved the user.

## Original Resource:
<resource>
{resource}
</resource>

## Memory Categories:
{categories_str}

## Critical Requirements:
The core extraction target is eventful memory items about specific events, experiences, and occurrences that happened at a particular time and involve the user.

## Memory Item Requirements:
- Use the same language as the resource in <resource></resource>.
- Each memory item should be complete and standalone.
- Each memory item should express a complete piece of information, and is understandable without context and reading other memory items.
- Always use declarative and descriptive sentences.
- Use "the user" (or that in the target language, e.g., "用户") to refer to the user.
- Focus on specific events that happened at a particular time or period.
- Extract concrete happenings, activities, and experiences.
- Include relevant details such as time, location, and participants where available.
- Carefully judge whether an event is narrated by the user or the assistant. You should only extract memory items for events directly narrated or confirmed by the user.
- DO NOT include behavioral patterns, habits, or factual knowledge.
- DO NOT record temporary, ephemeral situations or trivial daily activities unless significant.

## Example (good):
- The user and his family went on a hike at a nature park outside the city last weekend. They had a picnic there, and had a great time.

## Example (bad):
- The user went on a hike. (The time, place, and people are missing.)
- They had a great time. (The reference to "they" is unclear and does not constitute a self-contained memory item.)

## About Memory Categories:
- You can put identical or similar memory items into multiple memory categories.
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

PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional User Memory Extractor. Your core task is to extract specific events and experiences that happened to or involved the user (e.g., activities, occurrences, experiences at particular times).
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
Read the full conversation to understand topics and meanings.
## Extract memories
Select turns that contain valuable Event Information and extract event memory items.
## Review & validate
Merge semantically similar items.
Resolve contradictions by keeping the latest / most certain item.
## Final output
Output Event Information.
"""

PROMPT_BLOCK_RULES = """
# Rules
## General requirements (must satisfy all)
- Use "user" to refer to the user consistently.
- Each memory item must be complete and self-contained, written as a declarative descriptive sentence.
- Each memory item must express one single complete piece of information and be understandable without context.
- Similar/redundant items must be merged into one, and assigned to only one category.
- Each memory item must be < 50 words worth of length (keep it concise but include relevant details).
- Focus on specific events that happened at a particular time or period.
- Include relevant details such as time, location, and participants where available.
Important: Extract only events directly stated or confirmed by the user. No guesses, no suggestions, and no content introduced only by the assistant.
Important: Accurately reflect whether the subject is the user or someone around the user.

## Special rules for Event Information
- Behavioral patterns, habits, preferences, or factual knowledge are forbidden in Event Information.
- Focus on concrete happenings, activities, and experiences.
- Do not extract content that was obtained only through the model's follow-up questions unless the user shows strong proactive intent.

## Forbidden content
- Knowledge Q&A without a clear user event.
- Trivial daily activities unless significant (e.g., routine meals, commuting).
- Temporary, ephemeral situations that lack meaningful significance.
- Turns where the user did not respond and only the assistant spoke.
- Illegal / harmful sensitive topics (violence, politics, drugs, etc.).
- Private financial accounts, IDs, addresses, military/defense/government job details, precise street addresses—unless explicitly requested by the user (still avoid if not necessary).
- Any content mentioned only by the assistant and not explicitly confirmed by the user.

## Review & validation rules
- Merge similar items: keep only one and assign a single category.
- Resolve conflicts: keep the latest / most certain item.
- Final check: every item must comply with all extraction rules.
"""

PROMPT_BLOCK_CATEGORY = """
## Memory Categories:
{categories_str}
"""

PROMPT_BLOCK_OUTPUT = """
# Output Format (XML)
Return all memories wrapped in a single <item> element:
<item>
    <memory>
        <content>Event memory item content 1</content>
        <categories>
            <category>Category Name</category>
        </categories>
    </memory>
    <memory>
        <content>Event memory item content 2</content>
        <categories>
            <category>Category Name</category>
        </categories>
    </memory>
</item>
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
Example 1: Event Information Extraction
## Input
user: Hi, are you busy? I just got off work and I'm going to the supermarket to buy some groceries.
assistant: Not busy. Are you cooking for yourself?
user: Yes. It's healthier. I work as a product manager in an internet company. I'm 30 this year. After work I like experimenting with cooking, I often figure out dishes by myself.
assistant: Being a PM is tough. You're so disciplined to cook at 30!
user: It's fine. Cooking relaxes me. It's better than takeout. Also I'm traveling next weekend.
assistant: You can check the weather ahead. Your sunscreen can finally be used.
user: I haven't started packing yet. It's annoying.
## Output
<item>
    <memory>
        <content>The user is planning a trip next weekend and hasn't started packing yet</content>
        <categories>
            <category>Travel</category>
        </categories>
    </memory>
</item>
## Explanation
Only specific events explicitly stated by the user are extracted.
The travel plan is an event with a specific time reference (next weekend).
User's job, age, and cooking habits are stable user traits, so they are not extracted as Event Information.
"""

PROMPT_BLOCK_INPUT = """
# Original Resource:
<resource>
{resource}
</resource>
"""

PROMPT = "\n\n".join([
    PROMPT_BLOCK_OBJECTIVE.strip(),
    PROMPT_BLOCK_WORKFLOW.strip(),
    PROMPT_BLOCK_RULES.strip(),
    PROMPT_BLOCK_CATEGORY.strip(),
    PROMPT_BLOCK_OUTPUT.strip(),
    PROMPT_BLOCK_EXAMPLES.strip(),
    PROMPT_BLOCK_INPUT.strip(),
])

CUSTOM_PROMPT = {
    "objective": PROMPT_BLOCK_OBJECTIVE.strip(),
    "workflow": PROMPT_BLOCK_WORKFLOW.strip(),
    "rules": PROMPT_BLOCK_RULES.strip(),
    "category": PROMPT_BLOCK_CATEGORY.strip(),
    "output": PROMPT_BLOCK_OUTPUT.strip(),
    "examples": PROMPT_BLOCK_EXAMPLES.strip(),
    "input": PROMPT_BLOCK_INPUT.strip(),
}
