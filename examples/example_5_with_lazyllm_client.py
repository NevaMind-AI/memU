"""
Unified Example: LazyLLM Integration Demo
=========================================

This example merges functionalities from:
1. Example 1: Conversation Memory Processing
2. Example 2: Skill Extraction
3. Example 3: Multimodal Processing

It demonstrates how to use the LazyLLM backend for:
- Processing conversation history
- Extracting technical skills from logs
- Handling multimodal content (images + text)
- defaut source and model are from qwen

Usage:
    export MEMU_QWEN_API_KEY=your_api_key
    python examples/example_5_with_lazyllm_client.py
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

# Add src to sys.path FIRST before importing memu
project_root = Path(__file__).parent.parent
src_path = str(project_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from memu.app import MemoryService

# ==========================================
# PART 1: Conversation Memory Processing
# ==========================================


async def run_conversation_memory_demo(service):
    print("\n" + "=" * 60)
    print("PART 1: Conversation Memory Processing")
    print("=" * 60)

    conversation_folder = "examples/resources/conversations"

    total_items = 0
    categories = []

    try:
        print(f"  Processing folder: {conversation_folder}")
        result = await service.memorize(folder=conversation_folder)
        total_items = len(result.get("items", []))
        categories = result.get("categories", [])
        print(f"    ✓ Extracted {total_items} items")
    except Exception as e:
        print(f"  ✗ Error processing {conversation_folder}: {e}")

    # Output generation
    output_dir = "examples/output/lazyllm_example/conversation"
    os.makedirs(output_dir, exist_ok=True)
    await generate_markdown_output(categories, output_dir)
    print(f"✓ Conversation processing complete. Output: {output_dir}")


# ==========================================
# PART 2: Skill Extraction
# ==========================================


async def run_skill_extraction_demo(service):
    print("\n" + "=" * 60)
    print("PART 2: Skill Extraction from Logs")
    print("=" * 60)

    # Configure prompt for skill extraction
    skill_prompt = """
    You are analyzing an agent execution log. Extract the key actions taken, their outcomes, and lessons learned.

    Output MUST be valid XML wrapped in <skills> tags.
    Format:
    <skills>
        <memory>
            <content>
                [Action] Description...
                [Lesson] Key lesson...
            </content>
            <categories>
                <category>Category Name</category>
            </categories>
        </memory>
    </skills>

    Text: {resource}
    """

    # Update service config for skill extraction
    service.memorize_config.memory_types = ["skill"]
    service.memorize_config.memory_type_prompts = {"skill": skill_prompt}

    logs_folder = "examples/resources/logs"

    all_skills = []
    print(f"  Processing logs folder: {logs_folder}")
    try:
        result = await service.memorize(folder=logs_folder)
        for item in result.get("items", []):
            if item.get("memory_type") == "skill":
                all_skills.append(item.get("summary", ""))
        print(f"    ✓ Extracted {len(result.get('items', []))} skills")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Generate summary guide
    if all_skills:
        output_file = "examples/output/lazyllm_example/skills/skill_guide.md"
        await generate_skill_guide(all_skills, service, output_file)
        print(f"✓ Skill guide generated: {output_file}")


# ==========================================
# PART 3: Multimodal Memory
# ==========================================


async def run_multimodal_demo(service):
    print("\n" + "=" * 60)
    print("PART 3: Multimodal Memory Processing")
    print("=" * 60)

    # Configure for knowledge extraction
    xml_prompt = """
    Analyze content and extract key information.
    Output MUST be valid XML wrapped in <knowledge> tags.
    Format:
    <knowledge>
        <memory>
            <content>Extracted content...</content>
            <categories><category>category_name</category></categories>
        </memory>
    </knowledge>

    Content: {resource}
    """

    service.memorize_config.memory_types = ["knowledge"]
    service.memorize_config.memory_type_prompts = {"knowledge": xml_prompt}

    source_files = [
        "examples/resources/docs/doc1.txt",
        "examples/resources/images/image1.png",
    ]
    input_folder = "examples/output/lazyllm_example/multimodal_input"
    os.makedirs(input_folder, exist_ok=True)
    for src in source_files:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(input_folder, os.path.basename(src)))

    categories = []
    print(f"  Processing folder: {input_folder}")
    try:
        result = await service.memorize(folder=input_folder)
        categories = result.get("categories", [])
        print(f"    ✓ Extracted {len(result.get('items', []))} items")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    output_dir = "examples/output/lazyllm_example/multimodal"
    os.makedirs(output_dir, exist_ok=True)
    await generate_markdown_output(categories, output_dir)
    print(f"✓ Multimodal processing complete. Output: {output_dir}")


# ==========================================
# Helpers
# ==========================================


async def generate_markdown_output(categories, output_dir):
    for cat in categories:
        name = cat.get("name", "unknown")
        summary = cat.get("summary", "")
        if not summary:
            continue

        with open(os.path.join(output_dir, f"{name}.md"), "w", encoding="utf-8") as f:
            f.write(f"# {name.replace('_', ' ').title()}\n\n")
            cleaned = summary.replace("<content>", "").replace("</content>", "").strip()
            f.write(cleaned)


async def generate_skill_guide(skills, service, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    skills_text = "\n\n".join(skills)
    prompt = f"Summarize these skills into a guide:\n\n{skills_text}"

    # Use LazyLLM via service
    summary = await service.llm_client.chat(text=prompt)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(summary)


# ==========================================
# Main Entry
# ==========================================


async def main():
    print("Unified LazyLLM Example")
    print("=" * 60)
    # 1. Initialize Shared Service
    service = MemoryService(
        llm_profiles={
            "default": {
                "client_backend": "lazyllm_backend",
                "chat_model": "qwen3-max",
                "embed_model": "text-embedding-v3",
                "lazyllm_source": {
                    "source": "qwen",
                    "llm_source": "qwen",
                    "vlm_source": "qwen",
                    "embed_source": "qwen",
                    "stt_source": "qwen",
                    "vlm_model": "qwen-vl-plus",
                    "stt_model": "qwen-audio-turbo",
                },
            },
        }
    )

    # 2. Run Demos
    await run_conversation_memory_demo(service)
    # await run_skill_extraction_demo(service)
    # await run_multimodal_demo(service)


if __name__ == "__main__":
    asyncio.run(main())
