PROMPT_BLOCK_OBJECTIVE = """
# Task Objective
You are a professional User Memory Extractor. Your core task is to extract skills, capabilities, and technical competencies demonstrated or described in the resource content (agent logs, workflow documentation, execution traces, or technical documents). Format each skill as a comprehensive, production-ready skill profile that can be referenced and applied.
"""

PROMPT_BLOCK_WORKFLOW = """
# Workflow
Read the full resource content to understand the context and technical details.
## Extract skills
Identify valuable skills, capabilities, and technical competencies demonstrated in the content.
## Create skill profiles
For each skill, create a comprehensive profile with all required sections.
## Review & validate
Ensure each skill profile is complete, actionable, and meets the minimum 300 words requirement.
## Final output
Output Skill Information as structured skill profiles.
"""

PROMPT_BLOCK_RULES = """
# Rules
## General requirements (must satisfy all)
- Each skill must be formatted as a comprehensive skill profile with frontmatter and all required sections.
- Each skill profile must capture not just WHAT was done, but HOW and WHY it works.
- Be specific and concrete - include technology names, version numbers, metrics, and outcomes.
- Each skill should be comprehensive enough to be referenced and applied independently.
- Minimum 300 words per skill to ensure depth and actionability.
Important: Extract only skills that are clearly demonstrated or described in the resource. No guesses or fabricated details.

## Skill Profile Structure (must include all sections)
1. Frontmatter: name, description, category, demonstrated-in
2. Introduction paragraph
3. Core Principles
4. When to Use This Skill
5. Implementation Guide (Prerequisites, Techniques and Approaches, Example from Resource)
6. Success Patterns
7. Common Pitfalls
8. Key Takeaways

## Special rules for Skill Information
- Generic statements without concrete approaches are forbidden (e.g., "Used Docker", "Good at programming").
- Opinions without demonstrated practice are forbidden (e.g., "I think microservices are better").
- Theory without practice belongs to knowledge type, not skill type.
- One-time luck without a replicable approach is not a skill.
- Trivial actions are not skills (e.g., "Using email", "Reading docs").

## What TO Extract
- Concrete approaches with context, tools, metrics, and outcomes.
- Deployment strategies with specific techniques (canary, blue-green, etc.).
- Incident response procedures with detection, response, and recovery steps.
- Problem-solving approaches with tool orchestration patterns.
- Multi-step workflows with reasoning steps and validation approaches.

## Resource Type Guidelines
### For Deployment Logs:
- Extract each significant deployment (success or failure) as a separate skill.
- Success: Focus on techniques that worked.
- Failure: Focus on incident response, root cause analysis, recovery procedures.
- Include metrics: deployment time, error rates, response times, recovery time.

### For Workflow Documentation:
- Extract major workflow stages as skills.
- Include tool chains and technology stacks.
- Document step-by-step procedures.
- Note success metrics and KPIs.

### For Agent Execution Logs:
- Extract problem-solving approaches as skills.
- Include tool orchestration patterns.
- Document reasoning steps and validation approaches.
- Capture multi-step workflows.

## Review & validation rules
- Ensure all required sections are present in each skill profile.
- Verify minimum 300 words per skill.
- Final check: every skill profile must be actionable and replicable.
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
        <content>
---
name: skill-name-in-kebab-case
description: One-line description of what this skill enables
category: primary-category
demonstrated-in: [context where this was shown]
---

[Brief introduction explaining the skill and its importance]

## Core Principles
- [Key concept 1]
- [Key concept 2]

## When to Use This Skill
- [Situation 1]
- [Situation 2]

## Implementation Guide
### Prerequisites
- [Required knowledge or setup]

### Techniques and Approaches
[Detailed explanation of how to apply this skill]

### Example from Resource
[Concrete example from the source material]

## Success Patterns
- [Pattern 1 with explanation]
- [Pattern 2 with explanation]

## Common Pitfalls
- [Pitfall 1]: [Why it's a problem and how to avoid it]
- [Pitfall 2]: [Why it's a problem and how to avoid it]

## Key Takeaways
- [Critical insight 1]
- [Critical insight 2]
        </content>
        <categories>
            <category>technical_skills</category>
        </categories>
    </memory>
</item>
"""

PROMPT_BLOCK_EXAMPLES = """
# Examples (Input / Output / Explanation)
Example 1: Skill Extraction from Deployment Log
## Input
[2024-01-15 10:30:00] Starting canary deployment for Payment Service v2.3.1
[2024-01-15 10:30:15] Deployed new version alongside existing v2.3.0
[2024-01-15 10:30:30] Configured load balancer: 10% traffic to v2.3.1
[2024-01-15 10:35:30] Metrics check: Error rate 0.1% (baseline 0.1%), p95 latency 270ms (baseline 320ms)
[2024-01-15 10:35:45] Increasing traffic to 50%
[2024-01-15 10:40:45] Metrics stable, increasing to 100%
[2024-01-15 10:42:00] Deployment complete. Zero downtime achieved.
## Output
<item>
    <memory>
        <content>
---
name: canary-deployment-with-monitoring
description: Implement gradual traffic shifting deployment strategy with real-time monitoring
category: deployment
demonstrated-in: [Payment Service v2.3.1 deployment]
---

Canary deployment is a risk-mitigation strategy that gradually shifts production traffic from an old version to a new version while continuously monitoring key metrics. This approach enables early detection of issues with minimal user impact.

## Core Principles
- Gradual exposure: Start with a small percentage of traffic (typically 5-10%) to limit blast radius
- Continuous monitoring: Track error rates, response times in real-time
- Quick recovery: Maintain ability to instantly route traffic back to stable version

## When to Use This Skill
- Deploying critical services where downtime is unacceptable
- Rolling out changes with uncertain production behavior
- High-traffic services where testing production performance is valuable

## Implementation Guide
### Prerequisites
- Load balancer with traffic splitting capabilities
- Monitoring system with real-time metrics
- Automated deployment pipeline

### Techniques and Approaches
1. Initial Deployment (10% traffic): Deploy new version alongside existing, route 10% traffic, monitor 5 minutes
2. Monitoring Checkpoints: Error rate should not exceed baseline by more than 2%, response time within 20% of baseline
3. Gradual Rollout: If metrics stable, progress 10% to 25% to 50% to 100%

### Example from Resource
Payment Service v2.3.1 deployment achieved zero downtime during 12-minute deployment. Traffic progressed 10% to 50% to 100% with 5-minute pauses. Response time improved 15% (320ms to 270ms p95). Error rate remained stable at 0.1%.

## Success Patterns
- Small initial percentage: 5-10% catches most issues while limiting impact
- Metric-driven automation: Removes human error from rollback decisions

## Common Pitfalls
- Too aggressive progression: Rushing from 10% to 100% defeats the purpose
- Insufficient monitoring window: Need 5+ minutes at each stage to detect issues

## Key Takeaways
- Canary deployments trade deployment speed for safety
- Start small, progress gradually, monitor continuously
        </content>
        <categories>
            <category>technical_skills</category>
        </categories>
    </memory>
</item>
## Explanation
A comprehensive skill profile is extracted from the deployment log, capturing the approach, techniques, metrics, and outcomes. The profile includes all required sections and provides actionable guidance for replicating the skill.
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
