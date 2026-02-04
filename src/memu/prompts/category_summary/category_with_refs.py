"""
Category summary prompt with inline references to memory items.

This prompt instructs the LLM to include [ref:ITEM_ID] citations
when summarizing category content, linking statements to their
source memory items.
"""

PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional User Profile Synchronization Specialist. Your core objective is to accurately merge newly extracted user information items into the user's initial profile using only two operations: add and update.

IMPORTANT: You must include inline references to source memory items using the format [ref:ITEM_ID] when incorporating information from the provided memory items. This creates a traceable link between summary statements and their sources.
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
## Step 1: Preprocessing & Parsing
- Input sources:
  - User Initial Profile: structured, categorized, confirmed long-term user information.
  - Newly Extracted User Information Items: each item has an ID that MUST be referenced.
- Structure parsing:
  - Initial profile: extract categories and core content; preserve original wording style and format.
  - New items: note the item ID for each piece of information to include as [ref:ID].

## Step 2: Core Operations (Update / Add)
A. Update
- When updating existing information with new data, add the reference: "User is 30 years old [ref:item_abc123]"
- If multiple items support the same fact, include multiple refs: [ref:id1,id2]

B. Add
- When adding new information, always include the source reference
- Format: "User enjoys hiking on weekends [ref:item_xyz789]"

## Step 3: Merge & Formatting
- Structured ordering: present content by category order; omit empty categories.
- Formatting rules: strictly use Markdown (# for main title, ## for category titles).
- References: ensure every new or updated fact has at least one [ref:ITEM_ID] citation.

## Step 4: Summarize
Target length: {target_length}
- Summarize the updated user markdown profile to the target length.
- PRESERVE all [ref:ITEM_ID] citations in the summary.
- Use Markdown hierarchy.

## Step 5: Output
- Output only the updated user markdown profile with inline references.
- Use Markdown hierarchy.
- Do not include explanations, operation traces, or meta text.
"""

PROMPT_BLOCK_RULES = """
# Reference Rules
1. Every piece of information from new memory items MUST have a [ref:ITEM_ID] citation
2. Use the exact item ID provided in the input
3. Place references immediately after the relevant statement
4. Multiple sources can be cited: [ref:id1,id2]
5. Existing information without new updates does not need references
"""

PROMPT_BLOCK_OUTPUT = """
# Output Format (Markdown with References)
```markdown
# {category}
## <category name>
- User information item [ref:ITEM_ID]
- User information item [ref:ITEM_ID]
## <category name>
- User information item [ref:ITEM_ID,ITEM_ID2]
```

# Critical
- Always ensure that your output does not exceed {target_length} tokens.
- ALWAYS include [ref:ITEM_ID] for information from new memory items.
- You may merge or omit unimportant information to meet the length limit.
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output)

Topic:
Personal Basic Information

Original content:
<content>
# Personal Basic Information
## Basic Information
- The user is 28 years old
- The user currently lives in Beijing
</content>

New memory items with IDs:
<items>
- [item_a1b2c3] The user is 30 years old
- [item_d4e5f6] The user currently lives in Shanghai
- [item_g7h8i9] The user prefers Sichuan-style spicy food
</items>

Output:
# Personal Basic Information
## Basic Information
- The user is 30 years old [ref:item_a1b2c3]
- The user currently lives in Shanghai [ref:item_d4e5f6]
## Basic Preferences
- The user prefers Sichuan-style spicy food [ref:item_g7h8i9]
"""

PROMPT_BLOCK_INPUT = """
# Input
Topic:
{category}

Original content:
<content>
{original_content}
</content>

New memory items with IDs:
<items>
{new_memory_items_text}
</items>
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
