PROMPT_LEGACY = """
Your task is to read and understand the resource content between the user and the assistant, and, based on the given memory categories, extract knowledge and information that the user learned or discussed.

## Original Resource:
<resource>
{resource}
</resource>

## Memory Categories:
{categories_str}

## Critical Requirements:
The core extraction target is factual memory items that reflect knowledge, concepts, definitions, and factual information that the resource content suggests.

## Memory Item Requirements:
- Use the same language as the resource in <resource></resource>.
- Each memory item should be complete and standalone.
- Each memory item should express a complete piece of information, and is understandable without context and reading other memory items.
- Extract factual knowledge, concepts, definitions, and explanations
- Focus on objective information that can be learned or referenced
- Each item should be a descriptive sentence.
- Only extract meaningful knowledge, skip opinions or personal experiences
- Return empty array if no meaningful knowledge found

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
You are a professional User Memory Extractor. Your core task is to extract factual knowledge, concepts, definitions, and information that the user learned or discussed in the conversation.
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
Read the full conversation to understand topics and meanings.
## Extract memories
Select turns that contain valuable Knowledge Information and extract knowledge memory items.
## Review & validate
Merge semantically similar items.
Resolve contradictions by keeping the latest / most certain item.
## Final output
Output Knowledge Information.
"""

PROMPT_BLOCK_RULES = """
# Rules
## General requirements (must satisfy all)
- Each memory item must be complete and self-contained, written as a declarative descriptive sentence.
- Each memory item must express one single complete piece of information and be understandable without context.
- Similar/redundant items must be merged into one, and assigned to only one category.
- Each memory item must be < 50 words worth of length (keep it concise but include relevant details).
- Focus on factual knowledge, concepts, definitions, and explanations.
- Focus on objective information that can be learned or referenced.
Important: Extract only knowledge directly stated or discussed in the conversation. No guesses or unsupported extensions.

## Special rules for Knowledge Information
- Personal opinions, subjective preferences, or personal experiences are forbidden in Knowledge Information.
- Focus on objective facts, concepts, and explanations.
- User-specific traits, events, or behaviors are not knowledge items.

## Forbidden content
- Opinions or subjective statements without factual basis.
- Personal experiences or events (these belong to event type).
- User preferences or behavioral patterns (these belong to profile/behavior type).
- Trivial or commonly known facts that add no value.
- Illegal / harmful sensitive topics (violence, politics, drugs, etc.).
- Any content that is speculative or not clearly established in the conversation.

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
        <content>Knowledge memory item content 1</content>
        <categories>
            <category>Category Name</category>
        </categories>
    </memory>
    <memory>
        <content>Knowledge memory item content 2</content>
        <categories>
            <category>Category Name</category>
        </categories>
    </memory>
</item>
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
Example 1: Knowledge Information Extraction
## Input
user: I'm trying to understand how Python decorators work. Can you explain?
assistant: A decorator is a function that takes another function and extends its behavior without modifying it. It's a form of metaprogramming.
user: Oh I see, so it's like wrapping a function. I heard that the @ symbol is syntactic sugar for applying decorators.
assistant: Exactly! When you write @decorator above a function, it's equivalent to function = decorator(function).
user: That makes sense. By the way, I'm working on a project at my company using this.
## Output
<item>
    <memory>
        <content>In Python, a decorator is a function that takes another function and extends its behavior without modifying it</content>
        <categories>
            <category>Programming</category>
        </categories>
    </memory>
    <memory>
        <content>The @ symbol in Python is syntactic sugar for applying decorators, equivalent to function = decorator(function)</content>
        <categories>
            <category>Programming</category>
        </categories>
    </memory>
</item>
## Explanation
Only factual knowledge discussed and confirmed in the conversation is extracted.
The user's work project is a personal event/situation, not knowledge, so it is not extracted.
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
