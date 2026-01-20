"""
Example 6: Multimodal Processing -> Memory Category File (with LazyLLM)

This example demonstrates how to process multiple modalities (images, documents)
and generate a unified memory category JSON file using LazyLLM backend.

Usage:
    export LAZYLLM_QWEN_API_KEY=your_api_key
    python examples/example_6_multimodal_memory_with_lazyllm.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to sys.path FIRST before importing memu
project_root = Path(__file__).parent.parent
src_path = str(project_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
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

            # Content - full version
            if summary:
                cleaned_summary = summary.replace("<content>", "").replace("</content>", "").strip()
                f.write(f"{cleaned_summary}\n")
            else:
                f.write("*No content available*\n")

        generated_files.append(filename)

    return generated_files


async def main():
    """
    Process multiple modalities (images and documents) to generate memory categories using LazyLLM.

    This example:
    1. Initializes MemoryService with LazyLLM backend
    2. Processes documents and images
    3. Extracts unified memory categories across modalities
    4. Outputs the categories to files
    """
    print("Example 6: Multimodal Memory Processing with LazyLLM Backend")
    print("-" * 60)

    # Get LazyLLM API key from environment
    api_key = os.getenv("LAZYLLM_QWEN_API_KEY")
    if not api_key:
        msg = "Please set LAZYLLM_QWEN_API_KEY environment variable"
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

    # Initialize service with LazyLLM backend using llm_profiles
    # The "default" profile is required and used as the primary LLM configuration
    service = MemoryService(
        llm_profiles={
            "default": {
                "client_backend": "lazyllm_backend",
                "source": "qwen",
                "chat_model": "qwen-plus",
                "vlm_model": "qwen-vl-plus",
                "embed_model": "text-embedding-v3",
                "stt_model": "qwen-audio-turbo",
                "api_key": api_key,
            },
            "embedding": {
                "client_backend": "lazyllm_backend",
                "source": "qwen",
                "chat_model": "qwen-plus",
                "vlm_model": "qwen-vl-plus",
                "embed_model": "text-embedding-v3",
                "stt_model": "qwen-audio-turbo",
                "api_key": api_key,
            },
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
    print("\nProcessing resources with LazyLLM...")
    total_items = 0
    categories = []
    for resource_file, modality in resources:
        if not os.path.exists(resource_file):
            print(f"⚠ File not found: {resource_file}")
            continue

        try:
            print(f"  Processing: {resource_file} ({modality})")
            result = await service.memorize(resource_url=resource_file, modality=modality)
            total_items += len(result.get("items", []))
            # Categories are returned in the result and updated after each memorize call
            categories = result.get("categories", [])
            print(f"    ✓ Extracted {len(result.get('items', []))} items")
        except Exception as e:
            print(f"  ✗ Error processing {resource_file}: {e}")
            import traceback
            traceback.print_exc()

    # Write to output files
    output_dir = "examples/output/multimodal_example_lazyllm"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate individual Markdown files for each category
    generated_files = await generate_memory_md(categories, output_dir)

    print(f"\n" + "=" * 60)
    print(f"✓ Processed {len([r for r in resources if os.path.exists(r[0])])} files, extracted {total_items} items")
    print(f"✓ Generated {len(categories)} categories:")
    for cat in categories:
        print(f"  - {cat.get('name', 'unknown')}")
    print(f"✓ Output files ({len(generated_files)}):")
    for file in generated_files:
        print(f"  - {os.path.join(output_dir, file)}")
    print(f"✓ Output directory: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
