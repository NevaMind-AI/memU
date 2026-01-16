"""
Example 4: Multiple Conversations -> Memory Category File (Using OpenRouter)

This example demonstrates how to process multiple conversation files
and generate memory categories using OpenRouter as the LLM backend.

Usage:
    export OPENROUTER_API_KEY=your_api_key
    python examples/example_4_openrouter_memory.py
"""

import asyncio
import os
import sys

from memu.app import MemoryService

src_path = os.path.abspath("src")
sys.path.insert(0, src_path)


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
            if summary:
                cleaned_summary = summary.replace("<content>", "").replace("</content>", "").strip()
                f.write(f"{cleaned_summary}\n")
            else:
                f.write("*No content available*\n")

        generated_files.append(filename)

    return generated_files


async def main():
    """
    Process multiple conversation files and generate memory categories using OpenRouter.

    This example:
    1. Initializes MemoryService with OpenRouter API
    2. Processes conversation JSON files
    3. Extracts memory categories from conversations
    4. Outputs the categories to files
    """
    print("Example 4: Conversation Memory Processing (OpenRouter)")
    print("-" * 50)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        msg = "Please set OPENROUTER_API_KEY environment variable"
        raise ValueError(msg)

    # Initialize service with OpenRouter
    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "openrouter",
                "client_backend": "httpx",
                "base_url": "https://openrouter.ai",
                "api_key": api_key,
                "chat_model": "anthropic/claude-3.5-sonnet",  # you can use any model from openrouter.ai
                "embed_model": "openai/text-embedding-3-small",  # you can use any model from openrouter.ai
            },
        },
    )

    conversation_files = [
        "examples/resources/conversations/conv1.json",
        "examples/resources/conversations/conv2.json",
        "examples/resources/conversations/conv3.json",
    ]

    print("\nProcessing conversations...")
    total_items = 0
    categories = []

    for conv_file in conversation_files:
        if not os.path.exists(conv_file):
            print(f"Skipped: {conv_file} not found")
            continue

        try:
            print(f"Processing: {conv_file}")
            result = await service.memorize(resource_url=conv_file, modality="conversation")
            total_items += len(result.get("items", []))
            categories = result.get("categories", [])
        except Exception as e:
            print(f"Error processing {conv_file}: {e}")

    output_dir = "examples/output/openrouter_example"
    os.makedirs(output_dir, exist_ok=True)

    await generate_memory_md(categories, output_dir)

    print(f"\nProcessed {len(conversation_files)} files, extracted {total_items} items")
    print(f"Generated {len(categories)} categories")
    print(f"Output: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
