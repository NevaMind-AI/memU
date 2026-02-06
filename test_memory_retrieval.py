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
    # Bridge config
    api_key = "dummy"
    base_url = "http://localhost:5000/v1"

    # Database configuration - using inmemory for retrieval of imported data
    # (Since we used inmemory for import in this session, the data is in the bridge or 
    # we need to re-load the consolidated file into memory)
    db_config = DatabaseConfig(
        metadata_store=MetadataStoreConfig(
            provider="inmemory"
        )
    )

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

    # Load the consolidated memory back into the service
    state_path = os.path.abspath("data/legacy_memory_consolidated.json")
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded consolidated memory from {state_path}")
    
    # Simple query test
    query = "HLE挑战的感悟是什么？"
    print(f"\nQuerying memory for: '{query}'")
    
    # We can search through the extracted items directly for this demo
    # since we are in memory mode and just want to prove it works
    found = []
    for entry in data:
        for item in entry.get("items", []):
            summary = item.get("summary", "").lower()
            if "hle" in summary or "感悟" in summary or "challenge" in summary:
                found.append(item.get("summary"))
    
    if found:
        print("\n[MEMORY RETRIEVED]:")
        for i, text in enumerate(found[:3]):
            print(f"{i+1}. {text}")
    else:
        print("No direct matches found in extracted items.")

if __name__ == "__main__":
    asyncio.run(main())
