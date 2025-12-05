"""
Example 3: Multimodal Processing -> Memory Category File

This example demonstrates how to process multiple modalities (images, documents)
and generate a unified memory category JSON file.

Usage:
    export OPENAI_API_KEY=your_api_key
    python examples/example_3_multimodal_memory.py
"""

import asyncio
import os
import sys

from memu.app import MemoryService

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)


async def generate_memory_md(categories, output_dir):
    """Generate concise markdown files for each memory category."""

    os.makedirs(output_dir, exist_ok=True)

    generated_files = []

    for cat in categories:
        name = cat.get("name", "unknown")
        description = cat.get("description", "")
        summary = cat.get("summary", "")

        filename = f"{name}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            # Title
            formatted_name = name.replace("_", " ").title()
            f.write(f"# {formatted_name}\n\n")

            if description:
                f.write(f"*{description}*\n\n")

            # Content - concise version
            if summary:
                cleaned_summary = summary.replace("<content>", "").replace("</content>", "").strip()
                # Limit to first 500 characters for concise output
                if len(cleaned_summary) > 500:
                    cleaned_summary = cleaned_summary[:500] + "..."
                f.write(f"{cleaned_summary}\n")
            else:
                f.write("*No content available*\n")

        generated_files.append(filename)

    return generated_files


async def main():
    """
    Process multiple modalities (images and documents) to generate memory categories.

    This example:
    1. Initializes MemoryService with OpenAI API
    2. Processes documents and images
    3. Extracts unified memory categories across modalities
    4. Outputs the categories to files
    """
    print("Example 3: Multimodal Memory Processing")
    print("-" * 50)

    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    # Define custom categories for multimodal content
    multimodal_categories = [
        {"name": "technical_documentation", "description": "Technical documentation, guides, and tutorials"},
        {
            "name": "architecture_concepts",
            "description": "System architecture, design patterns, and structural concepts",
        },
        {"name": "best_practices", "description": "Best practices, recommendations, and guidelines"},
        {"name": "code_examples", "description": "Code snippets, examples, and implementation details"},
        {"name": "visual_diagrams", "description": "Visual concepts, diagrams, charts, and illustrations from images"},
    ]

    service = MemoryService(
        llm_config={
            "api_key": api_key,
            "chat_model": "gpt-4o-mini",
        },
        embedding_config={
            "api_key": api_key,
            "embed_model": "text-embedding-3-small",
        },
        memorize_config={"memory_categories": multimodal_categories},
    )

    # Resources to process (file_path, modality)
    resources = [
        ("examples/resources/docs/doc1.txt", "document"),
        ("examples/resources/docs/doc2.txt", "document"),
        ("examples/resources/images/image1.png", "image"),
    ]

    # Process each resource
    print("\nProcessing resources...")
    total_items = 0
    for resource_file, modality in resources:
        if not os.path.exists(resource_file):
            continue

        try:
            result = await service.memorize(resource_url=resource_file, modality=modality)
            total_items += len(result.get("items", []))
        except Exception as e:
            print(f"Error: {e}")

    # Extract and serialize categories
    categories = [cat.model_dump() for cat in service.store.categories.values()]

    # Write to output files
    output_dir = "examples/output/multimodal_example"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate individual Markdown files for each category
    await generate_memory_md(categories, output_dir)

    print(f"\n✓ Processed {len(resources)} files, extracted {total_items} items")
    print(f"✓ Generated {len(categories)} categories")
    print(f"✓ Output: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
