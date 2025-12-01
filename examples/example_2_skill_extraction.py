"""
Example 2: Workflow & Agent Logs -> Skill Extraction

This example demonstrates how to extract skills from workflow descriptions
and agent runtime logs, then output them to a Markdown file.

Usage:
    export OPENAI_API_KEY=your_api_key
    python examples/example_2_skill_extraction.py
"""

import asyncio
import os
import sys

from openai import AsyncOpenAI

from memu.app import MemoryService

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)


async def generate_skill_md(all_skills, service, output_file, attempt_number, total_attempts, is_final=False):
    """
    Use LLM to generate a concise task execution guide (skill.md).

    This creates a production-ready guide incorporating lessons learned from deployment attempts.
    """

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Prepare context for LLM
    skills_text = "\n\n".join([f"### From {skill_data['source']}\n{skill_data['skill']}" for skill_data in all_skills])

    # Get category summaries if available
    categories_text = ""
    if service.store.categories:
        categories_with_content = {
            cat_id: cat for cat_id, cat in service.store.categories.items() if cat.summary and cat.summary.strip()
        }
        if categories_with_content:
            categories_text = "\n\n".join([
                f"**{cat.name}**:\n{cat.summary}" for cat_id, cat in categories_with_content.items()
            ])

    # Construct prompt for LLM
    prompt = f"""Generate a concise production-ready task execution guide.

**Context**:
- Task: Production Microservice Deployment with Blue-Green Strategy
- Progress: {attempt_number}/{total_attempts} attempts
- Status: {"Complete" if is_final else f"v0.{attempt_number}"}

**Skills Learned**:
{skills_text}

{f"**Categories**:\n{categories_text}" if categories_text else ""}

**Required Structure**:

1. **Frontmatter** (YAML):
   - name: production-microservice-deployment
   - description: Brief description
   - version: {"1.0.0" if is_final else f"0.{attempt_number}.0"}
   - status: {"Production-Ready" if is_final else "Evolving"}

2. **Introduction**: What this guide does and when to use it

3. **Deployment Context**: Strategy, environment, goals

4. **Pre-Deployment Checklist**:
   - Actionable checks from lessons learned
   - Group by category (Database, Monitoring, etc.)
   - Mark critical items

5. **Deployment Procedure**:
   - Step-by-step instructions with commands
   - Include monitoring points

6. **Rollback Procedure**:
   - When to rollback (thresholds)
   - Exact commands
   - Expected recovery time

7. **Common Pitfalls & Solutions**:
   - Failures/issues encountered
   - Root cause, symptoms, solution

8. **Best Practices**:
   - What works well
   - Expected timelines

9. **Key Takeaways**: 3-5 most important lessons

**Style**:
- Use markdown with clear hierarchy
- Be specific and concise
- Technical and production-grade tone
- Focus on PRACTICAL steps

**CRITICAL**:
- ONLY use information from provided skills/lessons
- DO NOT make assumptions or add generic advice
- Extract ACTUAL experiences from the logs

Generate the complete markdown document now:"""

    client = AsyncOpenAI(api_key=service.llm_config.api_key)

    response = await client.chat.completions.create(
        model=service.llm_config.chat_model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert technical writer creating concise, production-grade deployment guides from real experiences.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=3000,
    )

    generated_content = response.choices[0].message.content

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(generated_content)

    return True


async def main():
    """
    Extract skills from agent logs using incremental memory updates.

    This example demonstrates INCREMENTAL LEARNING:
    1. Process files ONE BY ONE
    2. Each file UPDATES existing memory
    3. Category summaries EVOLVE with each new file
    4. Final output shows accumulated knowledge
    """
    print("Example 2: Incremental Skill Extraction")
    print("-" * 50)

    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    # Custom config for skill extraction
    skill_prompt = """
    You are analyzing an agent execution log. Extract the key actions taken, their outcomes, and lessons learned.

    For each significant action or phase:

    1. **Action/Phase**: What was being attempted?
    2. **Status**: SUCCESS ✅ or FAILURE ❌
    3. **What Happened**: What was executed
    4. **Outcome**: What worked/failed, metrics
    5. **Root Cause** (for failures): Why did it fail?
    6. **Lesson**: What did we learn?
    7. **Action Items**: Concrete steps for next time

    **IMPORTANT**:
    - Focus on ACTIONS and outcomes
    - Be specific: include actual metrics, errors, timing
    - ONLY extract information explicitly stated
    - DO NOT infer or assume information

    Extract ALL significant actions from the text:

    Text: {resource}
    """

    # Define custom categories
    skill_categories = [
        {"name": "deployment_execution", "description": "Deployment actions, traffic shifting, environment management"},
        {
            "name": "pre_deployment_validation",
            "description": "Capacity validation, configuration checks, readiness verification",
        },
        {
            "name": "incident_response_rollback",
            "description": "Incident response, error detection, rollback procedures",
        },
        {
            "name": "performance_monitoring",
            "description": "Metrics monitoring, performance analysis, bottleneck detection",
        },
        {"name": "database_management", "description": "Database capacity planning, optimization, schema changes"},
        {"name": "testing_verification", "description": "Testing, smoke tests, load tests, verification"},
        {"name": "infrastructure_setup", "description": "Kubernetes, containers, networking configuration"},
        {"name": "lessons_learned", "description": "Key reflections, root cause analyses, action items"},
    ]

    memorize_config = {
        "memory_types": ["skill"],
        "memory_type_prompts": {"skill": skill_prompt},
        "memory_categories": skill_categories,
    }

    # Initialize service
    service = MemoryService(
        llm_config={
            "api_key": api_key,
            "chat_model": "gpt-4o-mini",
        },
        embedding_config={
            "api_key": api_key,
            "embed_model": "text-embedding-3-small",
        },
        memorize_config=memorize_config,
    )

    # Resources to process
    resources = [
        ("examples/resources/logs/log1.txt", "document"),
        ("examples/resources/logs/log2.txt", "document"),
        ("examples/resources/logs/log3.txt", "document"),
    ]

    # Process each resource sequentially
    print("\nProcessing files...")
    all_skills = []

    for idx, (resource_file, modality) in enumerate(resources, 1):
        if not os.path.exists(resource_file):
            continue

        try:
            result = await service.memorize(resource_url=resource_file, modality=modality)

            # Extract skill items
            for item in result.get("items", []):
                if item.get("memory_type") == "skill":
                    all_skills.append({"skill": item.get("summary", ""), "source": os.path.basename(resource_file)})

            # Generate intermediate skill.md
            await generate_skill_md(
                all_skills=all_skills,
                service=service,
                output_file=f"examples/output/skill_example/log_{idx}.md",
                attempt_number=idx,
                total_attempts=len(resources),
            )

        except Exception as e:
            print(f"Error: {e}")

    # Generate final comprehensive skill.md
    await generate_skill_md(
        all_skills=all_skills,
        service=service,
        output_file="examples/output/skill_example/skill.md",
        attempt_number=len(resources),
        total_attempts=len(resources),
        is_final=True,
    )

    print(f"\n✓ Processed {len(resources)} files, extracted {len(all_skills)} skills")
    print(f"✓ Generated {len(service.store.categories)} categories")
    print("✓ Output: examples/output/skill_example/")


if __name__ == "__main__":
    asyncio.run(main())
