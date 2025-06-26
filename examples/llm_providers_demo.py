"""
PersonaLab LLM Providers Demo

This script demonstrates how to use all the different LLM providers available in PersonaLab.
Each provider has different setup requirements and capabilities.
"""

import os
import asyncio
from typing import Dict, Any

# Set up environment variables (you'll need to provide actual API keys)
# os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
# os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-api-key"
# os.environ["GOOGLE_API_KEY"] = "your-google-api-key"
# os.environ["AZURE_OPENAI_API_KEY"] = "your-azure-openai-api-key"
# os.environ["AZURE_OPENAI_ENDPOINT"] = "your-azure-endpoint"
# os.environ["COHERE_API_KEY"] = "your-cohere-api-key"
# os.environ["AWS_ACCESS_KEY_ID"] = "your-aws-access-key"
# os.environ["AWS_SECRET_ACCESS_KEY"] = "your-aws-secret-key"
# os.environ["TOGETHER_API_KEY"] = "your-together-api-key"
# os.environ["REPLICATE_API_TOKEN"] = "your-replicate-token"

from personalab.llm import LLMManager


def demo_individual_providers():
    """Demonstrate each LLM provider individually."""
    print("=== Individual LLM Providers Demo ===\n")
    
    # Test prompt
    prompt = "Explain quantum computing in one sentence."
    
    # 1. OpenAI
    print("1. OpenAI GPT:")
    try:
        from personalab.llm import OpenAILLM
        if os.getenv("OPENAI_API_KEY"):
            llm = OpenAILLM(model="gpt-3.5-turbo", temperature=0.7)
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API key provided")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 2. Anthropic Claude
    print("2. Anthropic Claude:")
    try:
        from personalab.llm import AnthropicLLM
        if os.getenv("ANTHROPIC_API_KEY"):
            llm = AnthropicLLM(model="claude-3-sonnet-20240229", temperature=0.7)
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API key provided")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 3. Google Gemini
    print("3. Google Gemini:")
    try:
        from personalab.llm import GoogleLLM
        if GoogleLLM and os.getenv("GOOGLE_API_KEY"):
            llm = GoogleLLM(model="gemini-pro", temperature=0.7)
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API key provided or library not installed")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 4. Azure OpenAI
    print("4. Azure OpenAI:")
    try:
        from personalab.llm import AzureOpenAILLM
        if (AzureOpenAILLM and os.getenv("AZURE_OPENAI_API_KEY") 
            and os.getenv("AZURE_OPENAI_ENDPOINT")):
            llm = AzureOpenAILLM(
                model="gpt-4", 
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                temperature=0.7
            )
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API key/endpoint provided or library not installed")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 5. Cohere
    print("5. Cohere:")
    try:
        from personalab.llm import CohereLLM
        if CohereLLM and os.getenv("COHERE_API_KEY"):
            llm = CohereLLM(model="command", temperature=0.7)
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API key provided or library not installed")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 6. AWS Bedrock
    print("6. AWS Bedrock:")
    try:
        from personalab.llm import BedrockLLM
        if (BedrockLLM and (os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"))):
            llm = BedrockLLM(
                model="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.7
            )
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No AWS credentials provided or library not installed")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 7. Together AI
    print("7. Together AI:")
    try:
        from personalab.llm import TogetherLLM
        if TogetherLLM and os.getenv("TOGETHER_API_KEY"):
            llm = TogetherLLM(
                model="meta-llama/Llama-2-7b-chat-hf",
                temperature=0.7
            )
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API key provided or library not installed")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 8. Replicate
    print("8. Replicate:")
    try:
        from personalab.llm import ReplicateLLM
        if ReplicateLLM and os.getenv("REPLICATE_API_TOKEN"):
            llm = ReplicateLLM(
                model="meta/llama-2-70b-chat",
                temperature=0.7
            )
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: No API token provided or library not installed")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # 9. Local Models
    print("9. Local Models (Ollama):")
    try:
        from personalab.llm import LocalLLM
        llm = LocalLLM(model="llama2", backend="ollama")
        if llm.is_available():
            response = llm.generate(prompt)
            print(f"   Response: {response.content}")
            print(f"   Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
        else:
            print("   Skipped: Ollama not available")
    except Exception as e:
        print(f"   Error: {e}")
    print()


def demo_llm_manager():
    """Demonstrate the LLM Manager with multiple providers."""
    print("=== LLM Manager Demo ===\n")
    
    # Create manager with quick setup
    manager = LLMManager.create_quick_setup()
    
    print("Available providers:")
    providers = manager.list_providers()
    for name, info in providers.items():
        status = "✓" if info["is_available"] else "✗"
        current = " (current)" if info["is_current"] else ""
        print(f"  {status} {name}: {info['model_info']['model']}{current}")
    print()
    
    if not providers:
        print("No providers available. Please set up API keys.")
        return
    
    # Test prompt
    prompt = "What is artificial intelligence?"
    
    # Generate with current provider
    print("Generating with current provider:")
    try:
        response = manager.generate(prompt, temperature=0.7)
        print(f"Response: {response.content}")
        print(f"Provider: {response.provider}, Model: {response.model}")
        print(f"Tokens: {response.total_tokens}, Time: {response.response_time:.2f}s")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Test fallback mechanism
    print("Testing fallback mechanism:")
    try:
        response = manager.generate_with_fallback(
            prompt, 
            provider_order=["nonexistent", "openai", "anthropic", "local"]
        )
        print(f"Successful provider: {response.provider}")
        print(f"Response: {response.content[:100]}...")
    except Exception as e:
        print(f"All providers failed: {e}")
    print()


async def demo_async_streaming():
    """Demonstrate async and streaming capabilities."""
    print("=== Async & Streaming Demo ===\n")
    
    # Test with OpenAI if available
    if os.getenv("OPENAI_API_KEY"):
        print("Streaming response from OpenAI:")
        try:
            from personalab.llm import OpenAILLM
            llm = OpenAILLM(model="gpt-3.5-turbo")
            
            prompt = "Write a short poem about coding."
            print("Prompt:", prompt)
            print("Response:", end=" ")
            
            async for chunk in llm.stream_async(prompt):
                print(chunk, end="", flush=True)
            print("\n")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Test with Google if available
    if os.getenv("GOOGLE_API_KEY"):
        print("Async response from Google Gemini:")
        try:
            from personalab.llm import GoogleLLM
            if GoogleLLM:
                llm = GoogleLLM(model="gemini-pro")
                response = await llm.generate_async("Explain machine learning briefly.")
                print(f"Response: {response.content}")
                print(f"Time: {response.response_time:.2f}s")
        except Exception as e:
            print(f"Error: {e}")
    print()


def demo_provider_comparison():
    """Compare responses from different providers."""
    print("=== Provider Comparison Demo ===\n")
    
    prompt = "Explain the concept of recursion in programming."
    
    providers_to_test = [
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-sonnet-20240229"),
        ("google", "gemini-pro"),
        ("cohere", "command")
    ]
    
    responses = {}
    
    for provider_name, model_name in providers_to_test:
        try:
            manager = LLMManager()
            manager.add_provider("test", provider_name, model_name)
            response = manager.generate(prompt, provider="test", temperature=0.7)
            responses[provider_name] = {
                "content": response.content,
                "tokens": response.total_tokens,
                "time": response.response_time
            }
        except Exception as e:
            responses[provider_name] = {"error": str(e)}
    
    # Display comparison
    for provider, result in responses.items():
        print(f"{provider.upper()}:")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Response: {result['content'][:200]}...")
            print(f"   Tokens: {result['tokens']}, Time: {result['time']:.2f}s")
        print()


def main():
    """Run all demos."""
    print("PersonaLab LLM Providers Demo")
    print("=" * 50)
    print()
    
    # Individual providers demo
    demo_individual_providers()
    
    # LLM Manager demo
    demo_llm_manager()
    
    # Async and streaming demo
    asyncio.run(demo_async_streaming())
    
    # Provider comparison
    demo_provider_comparison()
    
    print("Demo completed!")


if __name__ == "__main__":
    main() 