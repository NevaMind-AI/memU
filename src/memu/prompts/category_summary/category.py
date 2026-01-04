PROMPT_LEGACY = """
# Task Objective
You are a professional User Profile Synchronization Specialist. Your core objective is to accurately merge newly extracted user information items into the user's initial profile using only two operations: add and update.
Because no original conversation text is provided, active deletion is not allowed; only implicit replacement through newer items is permitted. The final output must be the updated, complete user profile.

# Workflow
## Step 1: Preprocessing & Parsing
- Input sources
User Initial Profile: structured, categorized, confirmed long-term user information.
Newly Extracted User Information Items.
- Structure parsing
Initial profile: extract categories and core content; preserve original wording style and format; build a category-content mapping.
New items: validate completeness and category correctness; mark each as Add or Update; distinguish stable facts from event-type information; extract dates/times (events only).
- Pre-validation
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


## Step 4: Summarize
Target length: {target_length}
Summarize the updated user markdown profile to the target length.
Use Markdown hierarchy.
Do not include explanations, operation traces, or meta text.
Control item length strictly; prioritize core information if needed.

## Step 5: Output
Output only the updated user markdown profile.
Use Markdown hierarchy.
Do not include explanations, operation traces, or meta text.
Control item length strictly; prioritize core information if needed.



# Output Format (Markdown)
```markdown
# {category}
## <category name>
- User information item
- User information item
...
## <category name>
- User information item
- User information item
...
```

# Examples (Input / Output / Explanation)
- Example 1: Basic Add & Update


Topic:
Personal Basic Information

Original content:
<content>
# Personal Basic Information
## Basic Information
- The user is 28 years old
- The user currently lives in Beijing
## Basic Preferences
- The user likes spicy food
## Core Traits
- The user is extroverted
</content>

New memory items:
<item>
- The user is 30 years old
- The user currently lives in Shanghai
- The user prefers Sichuan-style spicy food and dislikes sweet-spicy flavors
- The user enjoys hiking on weekends
- The user is meticulous
- The user ate Malatang today
</item>

Output
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


Your task is to read and analyze existing content and some new memory items, and then selectively update the content to reflect both the existing and new information.


# Input

Topic:
{category}

Original content:
<content>
{original_content}
</content>

New memory items:
<item>
{new_memory_items_text}
</item>


# Output format (Markdown)
```markdown
# {category}
## <category name>
- User information item
- User information item
...
## <category name>
- User information item
- User information item
...
```
"""


PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional User Profile Synchronization Specialist. Your core objective is to accurately merge newly extracted user information items into the user's initial profile using only two operations: add and update.
Because no original conversation text is provided, active deletion is not allowed; only implicit replacement through newer items is permitted. The final output must be the updated, complete user profile.
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
## Step 1: Preprocessing & Parsing
- Input sources
User Initial Profile: structured, categorized, confirmed long-term user information.
Newly Extracted User Information Items.
- Structure parsing
Initial profile: extract categories and core content; preserve original wording style and format; build a category-content mapping.
New items: validate completeness and category correctness; mark each as Add or Update; distinguish stable facts from event-type information; extract dates/times (events only).
- Pre-validation
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


## Step 4: Summarize
Target length: {target_length}
Summarize the updated user markdown profile to the target length.
Use Markdown hierarchy.
Cluster the memory items and update the <category name>.

## Step 5: Output
Output only the updated user markdown profile.
Use Markdown hierarchy.
Do not include explanations, operation traces, or meta text.
Control item length strictly; prioritize core information if needed.
"""

PROMPT_BLOCK_RULES = """
"""

PROMPT_BLOCK_OUTPUT = """
# Output Format (Markdown)
```markdown
# {category}
## <category name>
- User information item
- User information item
## <category name>
- User information item
- User information item
```
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
- Example 1: Basic Add & Update

Topic:
Personal Basic Information

Original content:
<content>
# Personal Basic Information
## Basic Information
- The user is 28 years old
- The user currently lives in Beijing
## Basic Preferences
- The user likes spicy food
## Core Traits
- The user is extroverted
</content>

New memory items:
<item>
- The user is 30 years old
- The user currently lives in Shanghai
- The user prefers Sichuan-style spicy food and dislikes sweet-spicy flavors
- The user enjoys hiking on weekends
- The user is meticulous
- The user ate Malatang today
</item>

Output
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
"""

PROMPT_BLOCK_INPUT = """
# Input
Topic:
{category}

Original content:
<content>
{original_content}
</content>

New memory items:
<item>
{new_memory_items_text}
</item>
"""

PROMPT = "\n\n".join([
    PROMPT_BLOCK_OBJECTIVE.strip(),
    PROMPT_BLOCK_WORKFLOW.strip(),
    PROMPT_BLOCK_RULES.strip(),
    PROMPT_BLOCK_OUTPUT.strip(),
    PROMPT_BLOCK_EXAMPLES.strip(),
    PROMPT_BLOCK_INPUT.strip(),
])

CUSTOM_PROMPT = {
    "objective": PROMPT_BLOCK_OBJECTIVE.strip(),
    "workflow": PROMPT_BLOCK_WORKFLOW.strip(),
    "rules": PROMPT_BLOCK_RULES.strip(),
    "output": PROMPT_BLOCK_OUTPUT.strip(),
    "examples": PROMPT_BLOCK_EXAMPLES.strip(),
    "input": PROMPT_BLOCK_INPUT.strip(),
}
