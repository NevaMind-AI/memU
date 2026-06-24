PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional Skill Extractor. Your core task is to extract operation logs: concrete
records of what was actually done, in what order, and with what outcome, so a later agent can
learn from the trace (e.g. the sequence of steps taken to accomplish a task and their results).
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
Read the full resource to understand the task and the actions taken.
## Extract logs
Select the parts that record concrete actions and outcomes, and extract one log item per
meaningful step or short coherent sequence.
## Review & validate
Merge redundant or duplicated steps.
Resolve contradictions by keeping the most accurate record.
## Final output
Output operation Log items.
"""

PROMPT_BLOCK_RULES = """
# Rules
## General requirements (must satisfy all)
- Each log item must be complete and self-contained, written as a past-tense record of an
  action and (when present) its result.
- Each log item must capture one step or one short coherent sequence, understandable without
  context.
- Similar/redundant logs must be merged into one, and assigned to only one skill.
- Each log item must be < 50 words worth of length (concise but informative).
- Preserve ordering signals (e.g. "first", "then", "after") when they matter.
Important: Extract only actions actually recorded in the resource. No guesses and no invented
steps.

## Special rules for Log Information
- Generalized reusable capabilities are NOT logs (those belong to the tool type).
- Personal facts, preferences, or unrelated events are NOT logs.

## Forbidden content
- Trivial chatter with no recorded action or outcome.
- Illegal / harmful sensitive operations.
- Speculative steps not grounded in the resource.

## Review & validation rules
- Merge duplicated steps: keep only one and assign a single skill.
- Final check: every item must comply with all extraction rules.
"""

PROMPT_BLOCK_CATEGORY = """
## Skills:
{categories_str}
"""

PROMPT_BLOCK_OUTPUT = """
# Output Format (XML)
Return all logs wrapped in a single <item> element:
<item>
    <memory>
        <content>Operation log item content 1</content>
        <categories>
            <category>Skill Name</category>
        </categories>
    </memory>
    <memory>
        <content>Operation log item content 2</content>
        <categories>
            <category>Skill Name</category>
        </categories>
    </memory>
</item>
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
Example 1: Log Extraction
## Input
assistant: I cloned the repo, ran `make install`, then `make test`. 2 tests failed due to a
missing env var, so I exported DATABASE_URL and re-ran; all tests passed.
## Output
<item>
    <memory>
        <content>Cloned the repo and ran `make install` followed by `make test`</content>
        <categories>
            <category>CI Setup</category>
        </categories>
    </memory>
    <memory>
        <content>Fixed 2 failing tests caused by a missing DATABASE_URL by exporting it and re-running; all tests then passed</content>
        <categories>
            <category>CI Setup</category>
        </categories>
    </memory>
</item>
## Explanation
Each item records what was actually done and its outcome, grouped under one skill.
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
