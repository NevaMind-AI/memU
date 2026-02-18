import asyncio
import os
import sys
import json

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from memu.app import MemoryService
from memu.app.settings import DatabaseConfig, MetadataStoreConfig

async def main():
    print("Starting legacy memory import into memU via OpenClaw Bridge...")
    
    # Bridge config
    api_key = "dummy"
    base_url = "http://localhost:5000/v1"

    # Database configuration - using inmemory for now
    db_config = DatabaseConfig(
        metadata_store=MetadataStoreConfig(
            provider="inmemory"
        )
    )

    # Initialize service pointing to our bridge
    service = MemoryService(
        database_config=db_config,
        llm_profiles={
            "default": {
                "base_url": base_url,
                "api_key": api_key,
                "chat_model": "openclaw-bridge",
                "embed_model": "fake-embeddings",
            }
        }
    )

    files_to_import = [
        r"C:\Users\16663\Desktop\Clawd-AI-Assistant\diary\2026-01-30.md",
        r"C:\Users\16663\Desktop\Clawd-AI-Assistant\diary\2026-01-31.md",
        r"C:\Users\16663\Desktop\Clawd-AI-Assistant\RUNNING_24H_GUIDE.md",
    ]

    extracted_data = []

    for file_path in files_to_import:
        if os.path.exists(file_path):
            print(f"Importing document: {file_path}")
            try:
                result = await service.memorize(resource_url=file_path, modality="document")
                num_items = len(result.get('items', []))
                print(f"  [SUCCESS] extracted {num_items} facts/insights")
                extracted_data.append({
                    "file": file_path,
                    "items": result.get('items', []),
                    "categories": result.get('categories', [])
                })
            except Exception as e:
                print(f"  [ERROR] importing {file_path}: {e}")
        else:
            print(f"  [NOT FOUND] File not found: {file_path}")

    # Summary of HLE progress
    hle_summary = """
    HLE (Holistic Language Education) Challenge Completion:
    Completed analysis of all 2500 problems in the HLE dataset on 2026-01-30.
    This was a milestone achievement involving cross-disciplinary knowledge in mathematics, physics, 
    humanities, and more. Key takeaways included the importance of interdisciplinary connections 
    and the omnipresence of mathematical logic.
    """
    
    print("Importing HLE Summary...")
    try:
        summary_path = os.path.abspath("data/hle_summary.txt")
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(hle_summary)
        
        result = await service.memorize(resource_url=summary_path, modality="document")
        print(f"  [SUCCESS] HLE summary integrated ({len(result.get('items', []))} items)")
        extracted_data.append({
            "file": "HLE_Summary",
            "items": result.get('items', []),
            "categories": result.get('categories', [])
        })
    except Exception as e:
        print(f"  [ERROR] importing HLE summary: {e}")

    # Final Categories
    print("\nFinal Categorized Memory:")
    categories = service.category_configs
    for cat in categories:
        if cat.description:
            print(f"- {cat.name}: {cat.description[:100]}...")

    # Save the consolidated memory state to a JSON file for persistent loading later
    state_path = os.path.abspath("data/legacy_memory_consolidated.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[DONE] Consolidated memory saved to: {state_path}")
    print("[DONE] Legacy memories successfully integrated into memU.")

if __name__ == "__main__":
    asyncio.run(main())