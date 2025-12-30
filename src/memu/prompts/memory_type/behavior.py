PROMPT_LEGACY = """
Your task is to read and understand the resource content between the user and the assistant, and, based on the given memory categories, extract behavioral patterns, routines, and solutions about the user.

## Original Resource:
<resource>
{resource}
</resource>

## Memory Categories:
{categories_str}

## Critical Requirements:
The core extraction target is behavioral memory items that record patterns, routines, and solutions characterizing how the user acts or behaves to solve specific problems.

## Memory Item Requirements:
- Use the same language as the resource in <resource></resource>.
- Extract patterns of behavior, routines, and solutions
- Focus on how the user typically acts, their preferences, and regular activities
- Each item can be either a single sentence concisely describing the pattern, routine, or solution, or a multi-line record with each line recording a specific step of the pattern, routine, or solution.
- Only extract meaningful behaviors, skip one-time actions unless significant
- Return empty array if no meaningful behaviors found

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
You are a professional User Memory Extractor. Your core task is to extract behavioral patterns, routines, and solutions that characterize how the user acts or behaves to solve specific problems.
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
Read the full conversation to understand topics and meanings.
## Extract memories
Select turns that contain valuable Behavior Information and extract behavioral memory items.
## Review & validate
Merge semantically similar items.
Resolve contradictions by keeping the latest / most certain item.
## Final output
Output Behavior Information.
"""

PROMPT_BLOCK_RULES = """
# Rules
## General requirements (must satisfy all)
- Use "user" to refer to the user consistently.
- Each memory item must be complete and self-contained, written as a declarative descriptive sentence.
- Each memory item must express one single complete piece of information and be understandable without context.
- Similar/redundant items must be merged into one, and assigned to only one category.
- Each memory item must be < 50 words worth of length (keep it concise but include relevant details).
- Focus on patterns of behavior, routines, and solutions.
- Focus on how the user typically acts, their preferences, and regular activities.
- Can include multi-line records with each line describing a specific step of the pattern, routine, or solution.
Important: Extract only behaviors directly stated or confirmed by the user. No guesses, no suggestions, and no content introduced only by the assistant.
Important: Accurately reflect whether the subject is the user or someone around the user.

## Special rules for Behavior Information
- One-time actions or specific events are forbidden in Behavior Information unless they demonstrate a significant pattern.
- Focus on recurring patterns, typical approaches, and established routines.
- Do not extract content that was obtained only through the model's follow-up questions unless the user shows strong proactive intent.

## Forbidden content
- Knowledge Q&A without a clear user behavior pattern.
- One-time events that do not reflect recurring behavior.
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
        <content>Behavior memory item content 1</content>
        <categories>
            <category>Category Name</category>
        </categories>
    </memory>
    <memory>
        <content>Behavior memory item content 2</content>
        <categories>
            <category>Category Name</category>
        </categories>
    </memory>
</item>
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
Example 1: Behavior Information Extraction
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
        <content>The user typically cooks for themselves after work instead of ordering takeout</content>
        <categories>
            <category>Daily Routine</category>
        </categories>
    </memory>
    <memory>
        <content>The user often experiments with cooking and figures out dishes by themselves</content>
        <categories>
            <category>Daily Routine</category>
        </categories>
    </memory>
</item>
## Explanation
Only behavioral patterns explicitly stated by the user are extracted.
Cooking after work and experimenting with dishes are recurring behaviors/routines.
User's job, age are stable traits (not behaviors). The travel plan is a one-time event, not a behavioral pattern.
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
