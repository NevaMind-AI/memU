PROMPT_LEGACY = """
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


PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional User Profile Synchronization Specialist. Your core objective is to accurately merge newly extracted user information items into the user's initial profile using only two operations: add and update.
Because no original conversation text is provided, active deletion is not allowed; only implicit replacement through newer items is permitted. The final output must be the updated, complete user profile.
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
## Step 1: Preprocessing & Parsing
Input sources
User Initial Profile: structured, categorized, confirmed long-term user information.
Newly Extracted User Information Items.
Structure parsing
Initial profile: extract categories and core content; preserve original wording style and format; build a category-content mapping.
New items: validate completeness and category correctness; mark each as Add or Update; distinguish stable facts from event-type information; extract dates/times (events only).
Pre-validation
Verify subject accuracy: clearly distinguish the user from related persons (family, friends, etc.).
Remove invalid items: vague, miscategorized, or non-user-information items.
Remove one-off events: temporary actions without long-term relevance (e.g., what the user ate today).

## Step 2: Core Operations (Update / Add)
A. Update
Conflict detection: compare new items with existing ones in the same category for semantic overlap (e.g., age update).
Validity priority: retain information that is more specific, clearer, and more certain.
Overwrite / supplement: replace outdated entries with new ones, ensuring no loss of core information.
Time integration (events only): retain dates/times and integrate them naturally; multiple events at the same time may be layered, but each entry must remain independently understandable.
B. Add
Deduplication check: ensure the new item is not identical or semantically similar to existing or updated items.
Category matching: place the item into the correct predefined category.
Insertion: add the item following the original profile's language and formatting style, concise and clear.

## Step 3: Merge & Formatting
Structured ordering: present content by category order; omit empty categories.
Formatting rules: strictly use Markdown (# for main title, ## for category titles).
Final validation
Consistency: no contradictions or duplicates.
Compliance: correct categories only; no explanatory or operational text.
Accuracy: subject clarity; natural time embedding; proper format.

## Step 4: Output
Output only the updated user profile.
Use Markdown hierarchy.
Do not include explanations, operation traces, or meta text.
Control item length strictly; prioritize core information if needed.
"""

PROMPT_BLOCK_OUTPUT = """
# Output Format (Markdown)

# Profile Title
## Category Name
- User information item
- User information item
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)

Example 1: Basic Add & Update
## Original content:
<content>
# Initial Profile
## Basic Information
- The user is 28 years old
- The user currently lives in Beijing
## Basic Preferences
- The user likes spicy food
## Core Traits
- The user is extroverted
</content>

## New memory items:
- The user is 30 years old
- The user currently lives in Shanghai
- The user prefers Sichuan-style spicy food and dislikes sweet-spicy flavors
- The user enjoys hiking on weekends
- The user is meticulous
- The user ate Malatang today

## Output
# Personal Basic Information
## Basic Information
- The user is 30 years old
- The user currently lives in Shanghai
## Basic Preferences
- The user prefers Sichuan-style spicy food and dislikes sweet-spicy flavors
- The user enjoys hiking on weekends
## Core Traits
- The user is extroverted
- The user is meticulous

Explanation
The "The user ate Malatang today" is a one-time daily action without long-term value and is therefore excluded.

Example 2: Time-Aware Conflict Update
## Original content:
<content>
# Initial Profile
## Basic Information
- Exercises three times per week
- Sleeps at 2 a.m. and wakes at 8 a.m.
## Basic Preferences
- Likes science fiction movies
</content>

## New memory items:
- From June 10, exercises twice per week, 30 minutes each session
- Sleeps at 3 a.m. and wakes at 9 a.m.
- Likes mystery movies and dislikes science fiction movies
- Started baking on June 15

## Output
# Lifestyle & Preferences
## User Habits
- The user sleeps at 3 a.m. and wakes at 9 a.m.
- From June 10, the user exercises twice per week, 30 minutes per session
## Basic Preferences
- The user likes mystery movies and dislikes science fiction movies
## User Events
- On June 15, the user started baking

Explanation
Habit and preference updates replace older conflicting entries.
The event includes a date and is retained as a user event.
"""

PROMPT_BLOCK_INPUT = """
## Topic:
{category}

## Original content:
<content>
{original_content}
</content>

## New memory items:
{new_memory_items_text}
"""

PROMPT = "\n\n".join([
    PROMPT_BLOCK_OBJECTIVE.strip(),
    PROMPT_BLOCK_WORKFLOW.strip(),
    PROMPT_BLOCK_OUTPUT.strip(),
    PROMPT_BLOCK_EXAMPLES.strip(),
    PROMPT_BLOCK_INPUT.strip(),
])

CUSTOM_PROMPT = {
    "objective": PROMPT_BLOCK_OBJECTIVE.strip(),
    "workflow": PROMPT_BLOCK_WORKFLOW.strip(),
    "output": PROMPT_BLOCK_OUTPUT.strip(),
    "examples": PROMPT_BLOCK_EXAMPLES.strip(),
    "input": PROMPT_BLOCK_INPUT.strip(),
}
