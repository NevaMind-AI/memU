"""
Example 5: Workflow & Agent Logs -> Skill Extraction (with LazyLLM)

This example demonstrates how to extract skills from workflow descriptions
and agent runtime logs using LazyLLM backend, then output them to a Markdown file.

Usage:
    export LAZYLLM_QWEN_API_KEY=your_api_key
    python examples/example_5_skill_extraction_with_lazyllm.py
"""

import asyncio
import os
import sys
from pathlib import Path
import lazyllm

# Add src to sys.path FIRST before importing memu
project_root = Path(__file__).parent.parent
src_path = str(project_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
from memu.app import MemoryService

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)


async def generate_skill_md(
    all_skills, service, output_file, attempt_number, total_attempts, categories=None, is_final=False
):
    """
    Use LLM to generate a concise task execution guide (skill.md).

    This creates a production-ready guide incorporating lessons learned from deployment attempts.
    """

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Prepare context for LLM
    skills_text = "\n\n".join([f"### From {skill_data['source']}\n{skill_data['skill']}" for skill_data in all_skills])

    # Get category summaries if available
    categories_text = ""
    if categories:
        categories_with_content = [cat for cat in categories if cat.get("summary") and cat.get("summary").strip()]
        if categories_with_content:
            categories_text = "\n\n".join([
                f"**{cat.get('name', 'unknown')}**:\n{cat.get('summary', '')}" for cat in categories_with_content
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

    # Use LazyLLM through MemoryService
    system_prompt = "You are an expert technical writer creating concise, production-grade deployment guides from real experiences."
    
    full_prompt = f"{system_prompt}\n\n{prompt}"
    generated_content = await service.llm_client.summarize(
        text=full_prompt,
        system_prompt=system_prompt,
    )

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(generated_content)

    return True


async def main():
    """
    Extract skills from agent logs using incremental memory updates with LazyLLM.

    This example demonstrates INCREMENTAL LEARNING:
    1. Process files ONE BY ONE
    2. Each file UPDATES existing memory
    3. Category summaries EVOLVE with each new file
    4. Final output shows accumulated knowledge
    """
    print("Example 5: Incremental Skill Extraction with LazyLLM")
    print("-" * 60)

    # Get LazyLLM API key from environment
    lazyllm.config.add("qwen_api_key", str, env="QWEN_API_KEY", description="Qwen API Key")
    with lazyllm.config.namespace("MEMU"):
        api_key = lazyllm.config['qwen_api_key']
    if not api_key:
        msg = "Please set MEMU_QWEN_API_KEY environment variable"
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

    Assign each extracted skill to one or more relevant categories from the following list:
    {categories_str}

    **IMPORTANT**:
    - Focus on ACTIONS and outcomes
    - Be specific: include actual metrics, errors, timing
    - ONLY extract information explicitly stated
    - DO NOT infer or assume information
    - Output MUST be valid XML wrapped in <skills> tags.

    Output format:
    <skills>
        <memory>
            <content>
                [Action] Description of the action and outcome.
                [Lesson] Key lesson learned.
            </content>
            <categories>
                <category>Category Name</category>
            </categories>
        </memory>
        ...
    </skills>

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

    # Initialize service with LazyLLM backend using llm_profiles
    # The "default" profile is required and used as the primary LLM configuration
    service = MemoryService(
        llm_profiles={
            "default": {
                "client_backend": "lazyllm_backend",
                "llm_source": "qwen",
                "vlm_source": "qwen",
                "embed_source": "qwen",
                "stt_source": "qwen",
                "chat_model": "qwen3-max",
                "vlm_model":"qwen-vl-plus",
                "stt_model":"qwen-audio-turbo",
                "embed_model": "text-embedding-v3",
                "api_key": api_key,
            },
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
    print("\nProcessing files with LazyLLM...")
    all_skills = []
    categories = []

    for idx, (resource_file, modality) in enumerate(resources, 1):
        if not os.path.exists(resource_file):
            print(f"⚠ File not found: {resource_file}")
            continue

        try:
            print(f"  Processing: {resource_file}")
            result = await service.memorize(resource_url=resource_file, modality=modality)

            # Extract skill items
            for item in result.get("items", []):
                if item.get("memory_type") == "skill":
                    all_skills.append({"skill": item.get("summary", ""), "source": os.path.basename(resource_file)})

            # Categories are returned in the result and updated after each memorize call
            categories = result.get("categories", [])

            # Generate intermediate skill.md
            await generate_skill_md(
                all_skills=all_skills,
                service=service,
                output_file=f"examples/output/skill_example_lazyllm/log_{idx}.md",
                attempt_number=idx,
                total_attempts=len(resources),
                categories=categories,
            )
            print(f"    ✓ Extracted {len([s for s in all_skills if s['source'] == os.path.basename(resource_file)])} skills")

        except Exception as e:
            print(f"  ✗ Error processing {resource_file}: {e}")
            import traceback
            traceback.print_exc()

    # Generate final comprehensive skill.md
    await generate_skill_md(
        all_skills=all_skills,
        service=service,
        output_file="examples/output/skill_example_lazyllm/skill.md",
        attempt_number=len(resources),
        total_attempts=len(resources),
        categories=categories,
        is_final=True,
    )

    print(f"\n" + "=" * 60)
    print(f"✓ Processed {len([r for r in resources if os.path.exists(r[0])])} files, extracted {len(all_skills)} skills")
    print(f"✓ Generated {len(categories)} categories")
    print("✓ Output: examples/output/skill_example_lazyllm/")


if __name__ == "__main__":
    asyncio.run(main())
