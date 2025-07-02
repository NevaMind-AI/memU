#!/usr/bin/env python3
"""
PersonaLab - LLM Client Usage Examples

This example demonstrates how to use the llm_client parameter in Persona class.
The llm_client parameter is now the recommended way to configure LLM providers.
"""

import os
from personalab import Persona
from personalab.llm import OpenAIClient, AnthropicClient, CustomLLMClient

def example_openai_client():
    """Example using OpenAI client with explicit configuration"""
    print("🤖 Example 1: Using OpenAI Client")
    
    # Create OpenAI client with specific configuration
    openai_client = OpenAIClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=150
    )
    
    # Pass the client to Persona
    persona = Persona(
        agent_id="openai_assistant",
        llm_client=openai_client,
        use_memory=True,
        use_memo=True
    )
    
    # Chat with the persona
    response = persona.chat("Hello, I'm interested in machine learning!")
    print(f"Assistant: {response}")
    
    persona.close()
    print("✅ OpenAI client example completed\n")

def example_anthropic_client():
    """Example using Anthropic client"""
    print("🤖 Example 2: Using Anthropic Client")
    
    # Check if Anthropic API key is available
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ ANTHROPIC_API_KEY not found, skipping Anthropic example")
        return
    
    # Create Anthropic client
    anthropic_client = AnthropicClient(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-sonnet-20240229",
        temperature=0.5,
        max_tokens=200
    )
    
    # Pass the client to Persona
    persona = Persona(
        agent_id="claude_assistant",
        llm_client=anthropic_client,
        use_memory=True,
        use_memo=True
    )
    
    # Chat with the persona
    response = persona.chat("Tell me about AI safety considerations.")
    print(f"Claude: {response}")
    
    persona.close()
    print("✅ Anthropic client example completed\n")

def example_custom_client():
    """Example using custom LLM client"""
    print("🤖 Example 3: Using Custom LLM Client")
    
    # Define a simple custom LLM function
    def my_custom_llm(messages, **kwargs):
        # This is a mock function - in practice, you'd call your actual LLM
        user_message = messages[-1]["content"]
        
        # Simple rule-based responses for demo
        if "hello" in user_message.lower():
            return f"Hello! You said: '{user_message}'"
        elif "weather" in user_message.lower():
            return "I'm a custom AI, I don't have real weather data, but it's probably nice!"
        else:
            return f"Custom AI received: '{user_message}'. This is a demo response."
    
    # Create custom client
    custom_client = CustomLLMClient(llm_function=my_custom_llm)
    
    # Pass the client to Persona
    persona = Persona(
        agent_id="custom_assistant",
        llm_client=custom_client,
        use_memory=True,
        use_memo=False  # Disable memo for this example
    )
    
    # Chat with the persona
    response1 = persona.chat("Hello there!")
    print(f"Custom AI: {response1}")
    
    response2 = persona.chat("How's the weather?")
    print(f"Custom AI: {response2}")
    
    persona.close()
    print("✅ Custom client example completed\n")

def example_default_usage():
    """Example using default configuration (reads from .env)"""
    print("🤖 Example 4: Using Default Configuration")
    
    # No llm_client specified - uses default OpenAI configuration from .env
    persona = Persona(
        agent_id="default_assistant",
        use_memory=True,
        use_memo=True
    )
    
    try:
        response = persona.chat("What's the capital of France?")
        print(f"Assistant: {response}")
        print("✅ Default configuration example completed\n")
    except Exception as e:
        print(f"⚠️ Default configuration failed: {e}")
        print("Make sure OPENAI_API_KEY is set in your .env file\n")
    finally:
        persona.close()

def example_client_comparison():
    """Example comparing different LLM clients on the same prompt"""
    print("🤖 Example 5: Comparing LLM Clients")
    
    prompt = "Explain quantum computing in one sentence."
    
    # Test with different clients
    clients = []
    
    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        openai_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            temperature=0.3
        )
        clients.append(("OpenAI GPT-3.5", openai_client))
    
    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        anthropic_client = AnthropicClient(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.3
        )
        clients.append(("Anthropic Claude", anthropic_client))
    
    # Compare responses
    for client_name, client in clients:
        persona = Persona(
            agent_id=f"comparison_{client_name.lower().replace(' ', '_')}",
            llm_client=client,
            use_memory=False,  # Disable for fair comparison
            use_memo=False
        )
        
        try:
            response = persona.chat(prompt)
            print(f"{client_name}: {response}")
        except Exception as e:
            print(f"{client_name}: Error - {e}")
        finally:
            persona.close()
    
    print("✅ Client comparison completed\n")

def main():
    """Run all examples"""
    print("🚀 PersonaLab LLM Client Usage Examples\n")
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment")
        print("Some examples may fail. Please set up your .env file.\n")
    
    # Run examples
    example_openai_client()
    example_anthropic_client()
    example_custom_client()
    example_default_usage()
    example_client_comparison()
    
    print("🎉 All examples completed!")
    print("\nKey takeaways:")
    print("1. Use llm_client parameter for full control over LLM configuration")
    print("2. Different LLM clients can be easily swapped")
    print("3. Default behavior still works for simple use cases")
    print("4. Custom LLM functions are supported for integration with any model")

if __name__ == "__main__":
    main() 