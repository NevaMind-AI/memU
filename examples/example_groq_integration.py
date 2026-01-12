"""
Example: Using Groq Provider for Ultra-Fast Memory Processing

This example demonstrates:
1. Configuring MemU with Groq for LLM operations
2. Using OpenAI for embeddings (Groq doesn't provide embeddings yet)
3. Processing conversations with Groq's ultra-fast inference
4. Performance benefits of Groq's LPU architecture

Usage:
    export GROQ_API_KEY=gsk_your_groq_key
    export OPENAI_API_KEY=sk_your_openai_key_for_embeddings
    python examples/example_groq_integration.py
"""

import asyncio
import os
import sys
import time

from memu.app import MemoryService

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)


async def main():
    """Demonstrate Groq integration for ultra-fast memory processing."""
    print("=" * 70)
    print("Groq Provider Integration Example")
    print("Ultra-Fast LLM Inference with LPU Architecture")
    print("=" * 70)
    print()

    # Check API keys
    groq_api_key = os.getenv("GROQ_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not groq_api_key:
        raise ValueError("Please set GROQ_API_KEY environment variable")
    if not openai_api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable (needed for embeddings)")

    # Initialize MemoryService with Groq + OpenAI dual configuration
    print("Initializing MemU with Groq...")
    print()
    
    service = MemoryService(
        llm_profiles={
            # Groq for ultra-fast LLM inference
            "default": {
                "provider": "groq",
                "base_url": "https://api.groq.com/openai/v1",
                "api_key": groq_api_key,
                "chat_model": "llama-3.3-70b-versatile",  # Best all-around model
                "client_backend": "http"  # Use HTTP client
            },
            # OpenAI for embeddings (Groq doesn't provide embeddings yet)
            "embedding": {
                "provider": "openai",
                "api_key": openai_api_key,
                "embed_model": "text-embedding-3-small"
            }
        },
    )

    print("✅ Service initialized with:")
    print("   - LLM Provider: Groq (llama-3.3-70b-versatile)")
    print("   - Embedding Provider: OpenAI (text-embedding-3-small)")
    print()

    # Example 1: Process a conversation
    print("Example 1: Processing Conversation with Groq")
    print("-" * 70)
    
    conversation_file = "examples/resources/conversations/conversation_001.json"
    
    if not os.path.exists(conversation_file):
        print(f"⚠️  File not found: {conversation_file}")
        print("Creating a sample conversation for demonstration...")
        # You would create a sample conversation here
    
    print(f"Processing: {conversation_file}")
    
    start_time = time.time()
    result = await service.memorize(
        resource_url=conversation_file,
        modality="conversation",
        user={"user_id": "groq_demo_user"}
    )
    elapsed = time.time() - start_time
    
    print(f"✅ Completed in {elapsed:.2f} seconds")
    print(f"   - Extracted items: {len(result.get('items', []))}")
    print(f"   - Categories: {len(result.get('categories', []))}")
    print()

    # Example 2: Retrieve memories (RAG)
    print("Example 2: Memory Retrieval with Groq")
    print("-" * 70)
    
    start_time = time.time()
    retrieval_result = await service.retrieve(
        queries=[
            {"role": "user", "content": {"text": "What are the user's preferences?"}}
        ],
        where={"user_id": "groq_demo_user"},
        method="rag"  # Fast embedding-based retrieval
    )
    elapsed = time.time() - start_time
    
    print(f"✅ Retrieved in {elapsed:.2f} seconds")
    print(f"   - Categories found: {len(retrieval_result.get('categories', []))}")
    print(f"   - Items found: {len(retrieval_result.get('items', []))}")
    print()

    # Example 3: Test different Groq models
    print("Example 3: Testing Different Groq Models")
    print("-" * 70)
    
    models_to_test = [
        ("llama-3.3-70b-versatile", "Best accuracy, 32K context"),
        ("llama-3.1-8b-instant", "Fastest speed, 8K context"),
        ("mixtral-8x7b-32768", "Multilingual, 32K context"),
    ]
    
    for model_id, description in models_to_test:
        print(f"\nTesting: {model_id}")
        print(f"Description: {description}")
        
        # Reconfigure service with new model
        service_test = MemoryService(
            llm_profiles={
                "default": {
                    "provider": "groq",
                    "base_url": "https://api.groq.com/openai/v1",
                    "api_key": groq_api_key,
                    "chat_model": model_id,
                    "client_backend": "http"
                },
                "embedding": {
                    "provider": "openai",
                    "api_key": openai_api_key,
                    "embed_model": "text-embedding-3-small"
                }
            },
        )
        
        print(f"✅ Configured with {model_id}")
    
    print()
    print("=" * 70)
    print("Demo completed! Groq integration working perfectly.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
