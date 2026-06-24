PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional Skill Extractor. Your core task is to extract reusable tools and
capabilities demonstrated in the resource: concrete, repeatable operations that an agent
could invoke again later (e.g. a command, an API call, a function, a procedure with clear
inputs and effects).
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
Read the full resource to understand what was done and how.
## Extract skills
Select the parts that describe a reusable operation and extract one tool item per distinct
capability.
## Review & validate
Merge semantically similar tools.
Resolve contradictions by keeping the most general, reusable form.
## Final output
Output reusable Tool items.
"""

PROMPT_BLOCK_RULES = """
# Rules
## General requirements (must satisfy all)
- Each tool item must be complete and self-contained, written as an imperative capability
  statement (what it does, with the inputs/effects that matter).
- Each tool item must describe one single reusable operation and be understandable without
  context.
- Similar/redundant tools must be merged into one, and assigned to only one skill.
- Each tool item must be < 50 words worth of length (concise but actionable).
- Prefer the generalized, reusable form over a one-off instance.
Important: Extract only operations actually demonstrated or described in the resource. No
guesses and no invented capabilities.

## Special rules for Tool Information
- One-off narration, results, or execution traces are NOT tools (those belong to the log type).
- Personal facts, preferences, or events are NOT tools.

## Forbidden content
- Trivial steps that carry no reusable value.
- Illegal / harmful sensitive operations.
- Speculative capabilities not grounded in the resource.

## Review & validation rules
- Merge similar tools: keep only one and assign a single skill.
- Final check: every item must comply with all extraction rules.
"""

PROMPT_BLOCK_CATEGORY = """
## Skills:
{categories_str}
"""

PROMPT_BLOCK_OUTPUT = """
# Output Format (XML)
Return all skills wrapped in a single <item> element:
<item>
    <memory>
        <content>Reusable tool item content 1</content>
        <categories>
            <category>Skill Name</category>
        </categories>
    </memory>
    <memory>
        <content>Reusable tool item content 2</content>
        <categories>
            <category>Skill Name</category>
        </categories>
    </memory>
</item>
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
Example 1: Tool Extraction
## Input
user: How do I find large files on Linux?
assistant: Run `du -ah /path | sort -rh | head -n 20` to list the 20 largest entries under a path.
user: Nice, and to delete one safely I just `rm -i file`.
## Output
<item>
    <memory>
        <content>List the largest files under a path with `du -ah <path> | sort -rh | head -n N`</content>
        <categories>
            <category>Filesystem</category>
        </categories>
    </memory>
    <memory>
        <content>Delete a file interactively (with confirmation) using `rm -i <file>`</content>
        <categories>
            <category>Filesystem</category>
        </categories>
    </memory>
</item>
## Explanation
Each item is a reusable command an agent could run again; both are grouped under one skill.
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
