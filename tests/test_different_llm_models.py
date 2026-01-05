"""
Test MemoryService with different LLM and Embedding providers.

Usage:
    # Test with OpenAI (default)
    OPENAI_API_KEY=xxx python tests/test_different_llm_models.py

    # Test with specific LLM provider
    python tests/test_different_llm_models.py --provider claude --api-key xxx

    # Test with separate embedding provider
    python tests/test_different_llm_models.py --provider claude --embed-provider voyage

    # Test with custom models
    python tests/test_different_llm_models.py --provider qwen --model qwen-max --embed-model text-embedding-v3

    # List all available providers
    python tests/test_different_llm_models.py --list-providers
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import Any


# LLM Provider configurations
@dataclass
class LLMProviderConfig:
    name: str
    base_url: str
    default_model: str
    env_key: str
    client_backend: str = "httpx"
    # Some providers share the same credentials for embeddings
    default_embed_model: str | None = None
    embed_provider: str | None = None  # If None, use same provider for embeddings


# Embedding Provider configurations
@dataclass
class EmbedProviderConfig:
    name: str
    base_url: str
    default_model: str
    env_key: str


LLM_PROVIDERS: dict[str, LLMProviderConfig] = {
    "openai": LLMProviderConfig(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        env_key="OPENAI_API_KEY",
        client_backend="sdk",
        default_embed_model="text-embedding-3-small",
    ),
    "claude": LLMProviderConfig(
        name="claude",
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-haiku-latest",  # or claude-3-5-sonnet-latest
        env_key="ANTHROPIC_API_KEY",
        # Claude has no embeddings, default to OpenAI
        embed_provider="openai",
    ),
    "gemini": LLMProviderConfig(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com",
        default_model="gemini-2.0-flash",  # or gemini-1.5-flash, gemini-1.5-pro
        env_key="GEMINI_API_KEY",
        # Gemini embeddings use different API format
        embed_provider="openai",
    ),
    "deepseek": LLMProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        env_key="DEEPSEEK_API_KEY",
        # DeepSeek has no embeddings, default to OpenAI
        embed_provider="openai",
    ),
    "openrouter": LLMProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai",
        default_model="openai/gpt-4o-mini",
        env_key="OPENROUTER_API_KEY",
        # OpenRouter has no embeddings, default to OpenAI
        embed_provider="openai",
    ),
    "qwen3": LLMProviderConfig(
        name="qwen3",
        base_url="https://dashscope.aliyuncs.com",
        default_model="qwen-plus",  # or qwen-turbo, qwen-max, qwq-plus
        env_key="DASHSCOPE_API_KEY",
        default_embed_model="text-embedding-v3",
    )
}

EMBED_PROVIDERS: dict[str, EmbedProviderConfig] = {
    "openai": EmbedProviderConfig(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="text-embedding-3-small",
        env_key="OPENAI_API_KEY",
    ),
    "voyage": EmbedProviderConfig(
        name="voyage",
        base_url="https://api.voyageai.com/v1",  # Must include /v1 for OpenAI SDK
        default_model="voyage-3-lite",
        env_key="VOYAGE_API_KEY",
    ),
    "jina": EmbedProviderConfig(
        name="jina",
        base_url="https://api.jina.ai/v1",  # Must include /v1 for OpenAI SDK
        default_model="jina-embeddings-v3",
        env_key="JINA_API_KEY",
    ),
    "qwen": EmbedProviderConfig(
        name="qwen",
        base_url="https://dashscope.aliyuncs.com",
        default_model="text-embedding-v3",
        env_key="DASHSCOPE_API_KEY",
    )
}


def list_providers() -> None:
    """Print available providers and their configurations."""
    print("\n" + "=" * 80)
    print("Available LLM Providers:")
    print("=" * 80)

    # Separate providers with and without native embeddings
    with_embeddings = []
    without_embeddings = []

    for name, config in LLM_PROVIDERS.items():
        if config.embed_provider:
            without_embeddings.append((name, config))
        else:
            with_embeddings.append((name, config))

    print("\n--- Providers with native embedding API ---")
    for name, config in with_embeddings:
        print(f"\n{name}:")
        print(f"  Base URL: {config.base_url}")
        print(f"  Default Model: {config.default_model}")
        print(f"  Embed Model: {config.default_embed_model}")
        print(f"  Environment Variable: {config.env_key}")

    print("\n--- Providers using external embedding API ---")
    for name, config in without_embeddings:
        print(f"\n{name}:")
        print(f"  Base URL: {config.base_url}")
        print(f"  Default Model: {config.default_model}")
        print(f"  Environment Variable: {config.env_key}")
        embed_cfg = EMBED_PROVIDERS.get(config.embed_provider or "openai")
        if embed_cfg:
            print(f"  Embed Provider: {config.embed_provider} ({embed_cfg.env_key})")

    print("\n" + "=" * 80)
    print("Available Embedding Providers:")
    print("=" * 80)
    for name, config in EMBED_PROVIDERS.items():
        print(f"\n{name}:")
        print(f"  Base URL: {config.base_url}")
        print(f"  Default Model: {config.default_model}")
        print(f"  Environment Variable: {config.env_key}")
    print()


async def test_with_provider(
    provider_name: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    embed_provider_name: str | None = None,
    embed_api_key: str | None = None,
    embed_model: str | None = None,
    embed_base_url: str | None = None,
) -> None:
    """Test MemoryService with a specific LLM and embedding provider."""
    from memu.app import MemoryService

    if provider_name not in LLM_PROVIDERS:
        print(f"Error: Unknown LLM provider '{provider_name}'")
        print(f"Available providers: {', '.join(LLM_PROVIDERS.keys())}")
        sys.exit(1)

    llm_config = LLM_PROVIDERS[provider_name]

    # Get LLM API key
    resolved_api_key = api_key or os.environ.get(llm_config.env_key)
    if not resolved_api_key:
        print(f"Error: LLM API key not provided. Set {llm_config.env_key} or use --api-key")
        sys.exit(1)

    resolved_model = model or llm_config.default_model
    resolved_base_url = base_url or llm_config.base_url

    # Determine embedding provider
    actual_embed_provider = embed_provider_name or llm_config.embed_provider or provider_name

    if actual_embed_provider not in EMBED_PROVIDERS and actual_embed_provider not in LLM_PROVIDERS:
        print(f"Error: Unknown embedding provider '{actual_embed_provider}'")
        print(f"Available: {', '.join(EMBED_PROVIDERS.keys())}")
        sys.exit(1)

    # Get embedding config
    if actual_embed_provider in EMBED_PROVIDERS:
        embed_config = EMBED_PROVIDERS[actual_embed_provider]
        resolved_embed_model = embed_model or embed_config.default_model
        resolved_embed_base_url = embed_base_url or embed_config.base_url
        embed_env_key = embed_config.env_key
        embed_provider_api_name = embed_config.name
    else:
        # Use LLM provider config for embeddings
        llm_embed_config = LLM_PROVIDERS[actual_embed_provider]
        resolved_embed_model = embed_model or llm_embed_config.default_embed_model or "text-embedding-3-small"
        resolved_embed_base_url = embed_base_url or llm_embed_config.base_url
        embed_env_key = llm_embed_config.env_key
        embed_provider_api_name = llm_embed_config.name

    # Get embedding API key
    resolved_embed_api_key = embed_api_key or os.environ.get(embed_env_key)
    if not resolved_embed_api_key:
        # If same provider, try reusing LLM key
        if actual_embed_provider == provider_name:
            resolved_embed_api_key = resolved_api_key
        else:
            print(f"Error: Embedding API key not provided. Set {embed_env_key} or use --embed-api-key")
            sys.exit(1)

    # Determine if we need separate profiles
    use_separate_embed_profile = (
        actual_embed_provider != provider_name or
        resolved_embed_base_url != resolved_base_url
    )

    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "example/example_conversation.json"))

    print("\n" + "=" * 60)
    print(f"[TEST] Starting test...")
    print("=" * 60)
    print(f"  LLM Provider: {provider_name}")
    print(f"  LLM Base URL: {resolved_base_url}")
    print(f"  LLM Model: {resolved_model}")
    print(f"  LLM Backend: {llm_config.client_backend}")
    print(f"  Embed Provider: {actual_embed_provider}")
    print(f"  Embed Base URL: {resolved_embed_base_url}")
    print(f"  Embed Model: {resolved_embed_model}")

    # Build LLM profiles config
    llm_profiles: dict[str, Any] = {
        "default": {
            "provider": provider_name,
            "base_url": resolved_base_url,
            "api_key": resolved_api_key,
            "chat_model": resolved_model,
            "client_backend": llm_config.client_backend,
            "embed_model": resolved_embed_model,
        }
    }

    if use_separate_embed_profile:
        # Configure separate embedding provider directly in the profile
        llm_profiles["default"]["embed_provider"] = embed_provider_api_name
        llm_profiles["default"]["embed_base_url"] = resolved_embed_base_url
        llm_profiles["default"]["embed_api_key"] = resolved_embed_api_key
        print(f"  Using separate embedding: {embed_provider_api_name} @ {resolved_embed_base_url}")

    try:
        service = MemoryService(
            llm_profiles=llm_profiles,
            database_config={
                "metadata_store": {"provider": "inmemory"},
            },
            retrieve_config={"method": "rag"},
        )

        # Memorize
        print(f"\n[MEMORIZE] Processing conversation...")
        memory = await service.memorize(
            resource_url=file_path,
            modality="conversation",
            user={"user_id": "test-user-123"},
        )
        print(f"  Created {len(memory.get('categories', []))} categories:")
        for cat in memory.get("categories", []):
            summary = cat.get("summary") or ""
            print(f"    - {cat.get('name')}: {summary[:60]}...")

        # Prepare queries
        queries = [
            {"role": "user", "content": {"text": "Tell me about preferences"}},
            {"role": "assistant", "content": {"text": "Sure, I'll tell you about their preferences"}},
            {"role": "user", "content": {"text": "What are they"}},
        ]

        # RAG-based retrieval
        print(f"\n[RETRIEVE] RAG method (using embeddings)...")
        service.retrieve_config.method = "rag"
        result_rag = await service.retrieve(queries=queries, where={"user_id": "test-user-123"})
        print("  Categories:")
        for cat in result_rag.get("categories", [])[:3]:
            summary = cat.get("summary") or cat.get("description", "")
            print(f"    - {cat.get('name')}: {summary[:60]}...")
        print("  Items:")
        for item in result_rag.get("items", [])[:3]:
            print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:80]}...")
        if result_rag.get("resources"):
            print("  Resources:")
            for res in result_rag.get("resources", [])[:3]:
                print(f"    - [{res.get('modality')}] {res.get('url', '')[:60]}...")

        # LLM-based retrieval
        print(f"\n[RETRIEVE] LLM method...")
        service.retrieve_config.method = "llm"
        result_llm = await service.retrieve(queries=queries, where={"user_id": "test-user-123"})
        print("  Categories:")
        for cat in result_llm.get("categories", [])[:3]:
            summary = cat.get("summary") or cat.get("description", "")
            print(f"    - {cat.get('name')}: {summary[:60]}...")
        print("  Items:")
        for item in result_llm.get("items", [])[:3]:
            print(f"    - [{item.get('memory_type')}] {item.get('summary', '')[:80]}...")
        if result_llm.get("resources"):
            print("  Resources:")
            for res in result_llm.get("resources", [])[:3]:
                print(f"    - [{res.get('modality')}] {res.get('url', '')[:60]}...")

        print(f"\n[SUCCESS] Test completed successfully!")

    except Exception as e:
        print(f"\n[FAILED] Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        raise


async def test_all_providers() -> None:
    """Test all providers that have API keys configured."""
    print("\n" + "=" * 60)
    print("Testing all configured providers...")
    print("=" * 60)
    print("\nNote: Providers without native embeddings will use OpenAI for embeddings.")
    print("      Make sure OPENAI_API_KEY is set for these providers.\n")

    results: dict[str, str] = {}

    for provider_name, config in LLM_PROVIDERS.items():
        api_key = os.environ.get(config.env_key)
        if not api_key:
            print(f"\n[{provider_name.upper()}] Skipped - {config.env_key} not set")
            results[provider_name] = "SKIPPED"
            continue

        # For providers without native embeddings, check if OpenAI key is available
        if config.embed_provider is not None:
            embed_config = EMBED_PROVIDERS.get(config.embed_provider)
            if embed_config:
                embed_key = os.environ.get(embed_config.env_key)
                if not embed_key:
                    print(f"\n[{provider_name.upper()}] Skipped - {embed_config.env_key} not set (needed for embeddings)")
                    results[provider_name] = f"SKIPPED (need {embed_config.env_key})"
                    continue

        try:
            await test_with_provider(provider_name)
            results[provider_name] = "PASSED"
        except Exception as e:
            results[provider_name] = f"FAILED: {e}"

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for provider, result in results.items():
        status_icon = "✓" if result == "PASSED" else "○" if "SKIPPED" in result else "✗"
        print(f"  {status_icon} {provider}: {result}")


async def test_embedding_providers() -> None:
    """Test all embedding providers with OpenAI as the LLM."""
    print("\n" + "=" * 60)
    print("Testing all embedding providers (with OpenAI LLM)...")
    print("=" * 60)

    # Check OpenAI key first
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("Error: OPENAI_API_KEY required for embedding provider tests")
        sys.exit(1)

    results: dict[str, str] = {}

    for embed_name, embed_config in EMBED_PROVIDERS.items():
        api_key = os.environ.get(embed_config.env_key)
        if not api_key:
            print(f"\n[{embed_name.upper()}] Skipped - {embed_config.env_key} not set")
            results[embed_name] = "SKIPPED"
            continue

        try:
            await test_with_provider(
                provider_name="openai",
                embed_provider_name=embed_name,
            )
            results[embed_name] = "PASSED"
        except Exception as e:
            results[embed_name] = f"FAILED: {e}"

    # Print summary
    print("\n" + "=" * 60)
    print("Embedding Provider Test Summary")
    print("=" * 60)
    for provider, result in results.items():
        status_icon = "✓" if result == "PASSED" else "○" if "SKIPPED" in result else "✗"
        print(f"  {status_icon} {provider}: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test MemoryService with different LLM and Embedding providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with OpenAI for both LLM and embeddings
  python tests/test_different_llm_models.py

  # Test with Claude LLM + OpenAI embeddings
  python tests/test_different_llm_models.py --provider claude

  # Test with Qwen LLM + Voyage embeddings
  python tests/test_different_llm_models.py --provider qwen --embed-provider voyage

  # Test with custom models
  python tests/test_different_llm_models.py --provider qwen --model qwen-max --embed-model text-embedding-v3

  # Test all LLM providers
  python tests/test_different_llm_models.py --all

  # Test all embedding providers
  python tests/test_different_llm_models.py --all-embeddings

  # List available providers
  python tests/test_different_llm_models.py --list-providers
        """,
    )

    parser.add_argument(
        "--provider", "-p",
        type=str,
        default="openai",
        help="LLM provider to test (default: openai)",
    )
    parser.add_argument(
        "--api-key", "-k",
        type=str,
        help="LLM API key (or set via environment variable)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        help="LLM model to use (uses provider default if not specified)",
    )
    parser.add_argument(
        "--base-url", "-u",
        type=str,
        help="LLM base URL override",
    )
    parser.add_argument(
        "--embed-provider",
        type=str,
        help="Embedding provider (default: same as LLM or OpenAI fallback)",
    )
    parser.add_argument(
        "--embed-api-key",
        type=str,
        help="Embedding API key (or set via environment variable)",
    )
    parser.add_argument(
        "--embed-model", "-e",
        type=str,
        help="Embedding model to use (uses provider default if not specified)",
    )
    parser.add_argument(
        "--embed-base-url",
        type=str,
        help="Embedding base URL override",
    )
    parser.add_argument(
        "--list-providers", "-l",
        action="store_true",
        help="List all available providers",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Test all LLM providers that have API keys configured",
    )
    parser.add_argument(
        "--all-embeddings",
        action="store_true",
        help="Test all embedding providers (with OpenAI LLM)",
    )

    args = parser.parse_args()

    if args.list_providers:
        list_providers()
        return

    if args.all:
        asyncio.run(test_all_providers())
    elif args.all_embeddings:
        asyncio.run(test_embedding_providers())
    else:
        asyncio.run(
            test_with_provider(
                provider_name=args.provider,
                api_key=args.api_key,
                model=args.model,
                base_url=args.base_url,
                embed_provider_name=args.embed_provider,
                embed_api_key=args.embed_api_key,
                embed_model=args.embed_model,
                embed_base_url=args.embed_base_url,
            )
        )


if __name__ == "__main__":
    main()
