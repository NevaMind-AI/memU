PROMPT_LEGACY = """
Your task is to read and understand the resource content (agent logs, workflow documentation, execution traces, or technical documents), and extract skills, capabilities, and technical competencies demonstrated or described in the content. Format each skill as a comprehensive, production-ready skill profile that can be referenced and applied.

## Original Resource:
<resource>
{resource}
</resource>

## Memory Categories:
{categories_str}

## Critical Requirements:
Extract skill-based memory items as comprehensive skill profiles that include:
1. **Skill Name**: Clear, memorable name for the skill
2. **Description**: What the skill enables and when to use it
3. **Context**: Situations where this skill was demonstrated
4. **Core Principles**: Fundamental guidelines and best practices
5. **Implementation Details**: Specific techniques, tools, and approaches
6. **Success Patterns**: What works well
7. **Common Pitfalls**: What to avoid

The core extraction target is actionable skill profiles that capture not just WHAT was done, but HOW and WHY it works.

## Skill Profile Structure:

For each extracted skill, create a comprehensive profile following this template:

```
---
name: skill-name-in-kebab-case
description: One-line description of what this skill enables and when to use it
category: primary-category
demonstrated-in: [list of contexts where this was shown]
---

[Brief introduction explaining the skill and its importance]

## Core Principles

[Key concepts and fundamental approaches that make this skill effective]

## When to Use This Skill

- Situation 1: [specific context]
- Situation 2: [specific context]
- [More situations as applicable]

## Implementation Guide

### Prerequisites
- [Required knowledge or setup]

### Techniques and Approaches
[Detailed explanation of how to apply this skill, including:]
- Specific methods used
- Tools and technologies involved
- Step-by-step process when applicable
- Metrics to track (error rates, response times, etc.)

### Example from Resource
[Concrete example from the source material showing this skill in action, including outcomes and metrics]

## Success Patterns

What works well when applying this skill:
- [Pattern 1 with explanation]
- [Pattern 2 with explanation]
- [More patterns]

## Common Pitfalls

What to avoid:
- **[Pitfall 1]**: [Why it's a problem and how to avoid it]
- **[Pitfall 2]**: [Why it's a problem and how to avoid it]
- [More pitfalls based on failures or lessons learned]

## Key Takeaways

- [Critical insight 1]
- [Critical insight 2]
- [Critical insight 3]
```

## Example Skill Profiles:

### Example 1: Canary Deployment

```
---
name: canary-deployment-with-monitoring
description: Implement gradual traffic shifting deployment strategy with real-time monitoring and automatic rollback capabilities
category: deployment
demonstrated-in: [Payment Service v2.3.1 deployment]
---

Canary deployment is a risk-mitigation strategy that gradually shifts production traffic from an old version to a new version while continuously monitoring key metrics. This approach enables early detection of issues with minimal user impact.

## Core Principles

- **Gradual exposure**: Start with a small percentage of traffic (typically 5-10%) to limit blast radius
- **Continuous monitoring**: Track error rates, response times, and business metrics in real-time
- **Automated decision-making**: Use predefined thresholds to trigger automatic rollbacks
- **Quick recovery**: Maintain ability to instantly route traffic back to stable version

## When to Use This Skill

- Deploying critical services where downtime is unacceptable
- Rolling out changes with uncertain production behavior
- High-traffic services where A/B testing production performance is valuable
- Services with complex dependencies where integration issues may emerge gradually

## Implementation Guide

### Prerequisites
- Load balancer with traffic splitting capabilities
- Monitoring system with real-time metrics (Prometheus, Grafana)
- Automated deployment pipeline (Jenkins, GitLab CI)
- Health check endpoints on both versions

### Techniques and Approaches

1. **Initial Deployment** (10% traffic):
   - Deploy new version alongside existing version
   - Configure load balancer to route 10% of traffic to new version
   - Monitor for 5-10 minutes

2. **Monitoring Checkpoints**:
   - Error rate comparison: New version should not exceed baseline by >2%
   - Response time (p95): Should remain within 20% of baseline
   - Business metrics: Transaction success rate, API call patterns

3. **Gradual Rollout**:
   - If metrics stable: 10% → 25% → 50% → 75% → 100%
   - Pause 5-10 minutes between each increment
   - Automated progression based on metric thresholds

4. **Rollback Triggers**:
   - Error rate >5%: Immediate rollback
   - Response time degradation >50%: Investigation required
   - Health check failures: Automatic rollback

### Example from Resource

Payment Service v2.3.1 deployment achieved:
- Zero downtime during 12-minute deployment
- Traffic progression: 10% → 50% → 100% with 2-minute pauses
- Response time improved 15% (320ms → 270ms p95)
- Error rate remained stable at 0.1% throughout
- New fraud detection algorithm safely rolled out to all users

## Success Patterns

What works well:
- **Small initial percentage**: 5-10% catches most issues while limiting impact
- **Metric-driven automation**: Removes human error from rollback decisions
- **Business metric monitoring**: Technical metrics alone miss some issues
- **Communication**: Notify stakeholders about canary status

## Common Pitfalls

What to avoid:
- **Too aggressive progression**: Rushing from 10% to 100% defeats the purpose
- **Insufficient monitoring window**: Need 5+ minutes at each stage to detect issues
- **Ignoring business metrics**: Technical health doesn't guarantee business success
- **Manual rollback only**: Human reaction time too slow for critical failures

## Key Takeaways

- Canary deployments trade deployment speed for safety
- Automation is critical for consistent, reliable rollbacks
- Start small (5-10%), progress gradually, monitor continuously
- Combine technical and business metrics for complete picture
```

### Example 2: Incident Response

```
---
name: rapid-incident-response
description: Quickly detect, diagnose, and resolve production incidents using automated monitoring and systematic troubleshooting
category: incident-response
demonstrated-in: [User Service v3.1.0 rollback]
---

Rapid incident response is the ability to quickly identify production problems, understand their root cause, and implement fixes or rollbacks to restore service. Speed and systematic approach are critical to minimizing customer impact.

## Core Principles

- **Fast detection**: Automated monitoring catches issues within minutes
- **Immediate action**: Rollback first, investigate later when customer impact is high
- **Systematic diagnosis**: Follow structured troubleshooting process
- **Learning culture**: Every incident is an opportunity to improve

## When to Use This Skill

- Production errors detected by monitoring alerts
- User-reported issues indicating service degradation
- Automated health checks failing
- Performance metrics exceeding thresholds

## Implementation Guide

### Prerequisites
- Comprehensive monitoring (logs, metrics, traces)
- Automated rollback capabilities
- On-call rotation and escalation procedures
- Incident management tools and runbooks

### Techniques and Approaches

1. **Detection Phase** (0-3 minutes):
   - Automated alerts trigger from monitoring thresholds
   - Error rate, response time, or business metric anomalies
   - Health check failures or pod restart loops

2. **Initial Response** (3-5 minutes):
   - Assess severity: Customer-facing? Data loss risk?
   - Decision: Rollback immediately or investigate first?
   - High severity → Immediate rollback
   - Low severity → Investigate with time limit

3. **Rollback Execution** (2-4 minutes):
   - Automated: Trigger rollback through deployment pipeline
   - Manual: Revert Helm release or switch traffic to previous version
   - Verify: Confirm metrics return to baseline

4. **Root Cause Analysis** (Post-incident):
   - Review logs, metrics, and deployment changes
   - Identify configuration drift, missing variables, performance issues
   - Document findings and create action items

### Example from Resource

User Service v3.1.0 incident:
- Detection: Error rate spiked 0.2% → 5.1% within 30 seconds
- Response: Automatic rollback triggered at threshold in 2 minutes
- Recovery: Service restored to v3.0.9, error rate normalized in 4 minutes total
- Root cause: Missing AUTH_REFRESH_SECRET environment variable in production
- No customer impact due to fast automated rollback

## Success Patterns

What works well:
- **Automated thresholds**: Remove human decision-making delay
- **Clear severity criteria**: Know when to rollback vs investigate
- **Runbooks**: Pre-documented procedures for common issues
- **Blameless post-mortems**: Focus on systemic improvements, not individual errors

## Common Pitfalls

What to avoid:
- **Investigation paralysis**: Spending too long diagnosing while customers suffer
- **Manual-only rollback**: Automation is 5-10x faster
- **Configuration drift**: Staging and production environment inconsistency
- **Skipping post-mortems**: Missing opportunity to prevent recurrence

## Key Takeaways

- Speed matters: Every minute of downtime impacts customers and business
- Automate rollback decisions based on objective metrics
- Rollback first, investigate second for high-severity incidents
- Use incidents to improve systems, not blame people
```

## What NOT to Extract as Skills:

❌ **Generic statements**: "Used Docker", "Good at programming"
❌ **Opinions**: "I think microservices are better"
❌ **Theory without practice**: "Kubernetes is an orchestrator" (that's knowledge)
❌ **One-time luck**: "Fixed a bug" without approach
❌ **Trivial actions**: "Using email", "Reading docs"

✅ **DO Extract**: Concrete approaches with context, tools, metrics, and outcomes

## About Memory Categories:
- You can put identical or similar skill items into multiple memory categories.
- Do not create new memory categories. Please only generate in the given memory categories.
- Focus on categories like: technical_skills, work_life, knowledge, experiences

## Memory Item Content Requirements:
- *ALWAYS* use the same language as the resource in <resource></resource>.
- Format as structured markdown with frontmatter (---, name, description, category, demonstrated-in, ---)
- Include all sections: Core Principles, When to Use, Implementation Guide, Success Patterns, Common Pitfalls, Key Takeaways
- Be specific and concrete - include technology names, version numbers, metrics, and outcomes
- Each skill should be comprehensive enough to be referenced and applied independently
- Minimum 300 words per skill to ensure depth and actionability
- If the original resource contains emojis or other special characters, ignore them and output in plain text.

## Special Instructions for Different Resource Types:

### For Deployment Logs:
- Extract each significant deployment (success or failure) as a separate skill
- Success: Focus on techniques that worked (canary, blue-green, performance optimization)
- Failure: Focus on incident response, root cause analysis, recovery procedures
- Include metrics: deployment time, error rates, response times, recovery time

### For Workflow Documentation:
- Extract major workflow stages as skills (CI/CD pipeline, testing strategy, monitoring setup)
- Include tool chains and technology stacks
- Document step-by-step procedures
- Note success metrics and KPIs

### For Agent Execution Logs:
- Extract problem-solving approaches as skills (competitive analysis, data processing, decision-making)
- Include tool orchestration patterns
- Document reasoning steps and validation approaches
- Capture multi-step workflows

# Response Format (JSON):
{{
    "memories_items": [
        {{
            "content": "MUST be a complete markdown skill profile starting with --- frontmatter, then sections. Format:
---
name: skill-name
description: one line description
category: category-name
demonstrated-in: [context]
---

[Introduction paragraph]

## Core Principles
[bullet points]

## When to Use This Skill
[bullet points]

## Implementation Guide
### Prerequisites
### Techniques and Approaches
### Example from Resource

## Success Patterns
[bullet points]

## Common Pitfalls
[bullet points]

## Key Takeaways
[bullet points]

Minimum 300 words total.",
            "categories": [list of memory categories]
        }}
    ]
}}

CRITICAL: The content field MUST contain the complete markdown text with ALL sections, not a summary paragraph. This is a skill documentation page, not a description.
"""

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
