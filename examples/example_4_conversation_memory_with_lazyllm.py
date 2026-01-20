"""
Example 4: Multiple Conversations -> Memory Category File with LazyLLM Backend

This example demonstrates how to process multiple conversation files
and generate a memory category JSON file using the LazyLLM backend.

Usage:
    export LAZYLLM_QWEN_API_KEY=your_api_key
    python examples/example_4_conversation_memory_with_lazyllm.py
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
    Process multiple conversation files and generate memory categories using LazyLLM.

    This example:
    1. Initializes MemoryService with LazyLLM backend
    2. Processes conversation JSON files
    3. Extracts memory categories from conversations
    4. Outputs the categories to files
    """
    print("Example 4: Conversation Memory Processing with LazyLLM Backend")
    print("-" * 60)

    # Get LazyLLM API key from environment
    # api_key = os.getenv("LAZYLLM_QWEN_API_KEY")
    api_key = os.getenv("LAZYLLM_QWEN_API_KEY")
    if not api_key:
        msg = "Please set LAZYLLM_QWEN_API_KEY environment variable"
        raise ValueError(msg)
    
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
    )

    # Conversation files to process
    conversation_files = [
        "examples/resources/conversations/conv1.json",
        "examples/resources/conversations/conv2.json",
        "examples/resources/conversations/conv3.json",
    ]

    # Process each conversation
    print("\nProcessing conversations with LazyLLM...")
    total_items = 0
    categories = []
    for conv_file in conversation_files:
        if not os.path.exists(conv_file):
            print(f"⚠ File not found: {conv_file}")
            continue

        try:
            print(f"  Processing: {conv_file}")
            result = await service.memorize(resource_url=conv_file, modality="conversation")
            total_items += len(result.get("items", []))
            # Categories are returned in the result and updated after each memorize call
            categories = result.get("categories", [])
            print(f"    ✓ Extracted {len(result.get('items', []))} items")
        except Exception as e:
            print(f"  ✗ Error processing {conv_file}: {e}")
            import traceback
            traceback.print_exc()

    # Write to output files
    output_dir = "examples/output/conversation_example_lazyllm"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate individual Markdown files for each category
    generated_files = await generate_memory_md(categories, output_dir)

    print(f"\n" + "=" * 60)
    print(f"✓ Processed {len([f for f in conversation_files if os.path.exists(f)])} files")
    print(f"✓ Extracted {total_items} total items")
    print(f"✓ Generated {len(categories)} categories:")
    for cat in categories:
        print(f"  - {cat.get('name', 'unknown')}")
    print(f"✓ Output files ({len(generated_files)}):")
    for file in generated_files:
        print(f"  - {os.path.join(output_dir, file)}")
    print(f"✓ Output directory: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
