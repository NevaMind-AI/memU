"""
Example 1: Multiple Conversations -> Memory Category File

This example demonstrates how to process multiple conversation files
and generate a memory category JSON file.

Usage:
    export OPENAI_API_KEY=your_api_key
    python examples/example_1_conversation_memory.py
"""

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Add src to sys.path before importing memu from a source checkout.
src_path = str(ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from memu import MemoryService


async def generate_memory_md(categories, output_dir):
    """Generate concise markdown files for each memory category."""

    os.makedirs(output_dir, exist_ok=True)

    generated_files = []

    for cat in categories:
        name = cat.get("name", "unknown")
        summary = cat.get("summary", "")

        filename = f"{name}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            # Title
            # Content - concise version
            if summary:
                cleaned_summary = summary.replace("<content>", "").replace("</content>", "").strip()
                f.write(f"{cleaned_summary}\n")
            else:
                f.write("*No content available*\n")

        generated_files.append(filename)

    return generated_files


async def main():
    """
    Process multiple conversation files and generate memory categories.

    This example:
    1. Initializes MemoryService with OpenAI API
    2. Processes conversation JSON files
    3. Extracts memory categories from conversations
    4. Outputs the categories to files
    """
    print("Example 1: Conversation Memory Processing")
    print("-" * 50)

    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    # Initialize service with OpenAI using llm_profiles
    # The "default" profile is required and used as the primary LLM configuration
    service = MemoryService(
        llm_profiles={
            "default": {
                "api_key": api_key,
                "chat_model": "gpt-4o-mini",
            },
        },
    )

    # Conversation files to process
    conversation_files = [
        ROOT / "examples" / "resources" / "conversations" / "conv1.json",
        ROOT / "examples" / "resources" / "conversations" / "conv2.json",
        ROOT / "examples" / "resources" / "conversations" / "conv3.json",
    ]

    # Process each conversation
    print("\nProcessing conversations...")
    total_items = 0
    categories = []
    for conv_file in conversation_files:
        if not conv_file.exists():
            continue

        try:
            result = await service.memorize(resource_url=str(conv_file), modality="conversation")
            total_items += len(result.get("items", []))
            # Categories are returned in the result and updated after each memorize call
            categories = result.get("categories", [])
        except Exception as e:
            print(f"Error: {e}")

    # Write to output files
    output_dir = ROOT / "examples" / "output" / "conversation_example"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate individual Markdown files for each category
    await generate_memory_md(categories, output_dir)

    print(f"\n[OK] Processed {len(conversation_files)} files, extracted {total_items} items")
    print(f"[OK] Generated {len(categories)} categories")
    print(f"[OK] Output: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
