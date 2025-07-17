"""
DeepSeek Client Usage Example

This example demonstrates how to use the DeepSeekClient with Azure AI Inference.
"""

import os
from memu.llm import DeepSeekClient

def main():
    """Main example function"""
    
    # Initialize DeepSeek client
    # You can set these environment variables:
    # DEEPSEEK_API_KEY = your DeepSeek API key
    # DEEPSEEK_ENDPOINT = your DeepSeek endpoint (e.g., "https://ai-sairin12027701ai851284620530.services.ai.azure.com/models")
    
    client = DeepSeekClient(
        api_key="<YOUR_API_KEY>",  # or set DEEPSEEK_API_KEY environment variable
        endpoint="https://ai-sairin12027701ai851284620530.services.ai.azure.com/models",  # or set DEEPSEEK_ENDPOINT
        model_name="DeepSeek-V3-0324",
        api_version="2024-05-01-preview"
    )
    
    # Simple chat example
    print("=== Simple Chat Example ===")
    simple_response = client.simple_chat("What is the capital of France?")
    print(f"Response: {simple_response}")
    
    # Chat completion example with detailed parameters
    print("\n=== Chat Completion Example ===")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "I am going to Paris, what should I see?"}
    ]
    
    response = client.chat_completion(
        messages=messages,
        temperature=0.8,
        max_tokens=2048,
        top_p=0.1,
        presence_penalty=0.0,
        frequency_penalty=0.0
    )
    
    if response.success:
        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        print(f"Usage: {response.usage}")
    else:
        print(f"Error: {response.error}")

    # Function calling example (if supported by DeepSeek)
    print("\n=== Function Calling Example ===")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    messages_with_tools = [
        {"role": "system", "content": "You are a helpful assistant with access to weather information."},
        {"role": "user", "content": "What's the weather like in Tokyo?"}
    ]
    
    response_with_tools = client.chat_completion(
        messages=messages_with_tools,
        tools=tools,
        temperature=0.2
    )
    
    if response_with_tools.success:
        print(f"Response: {response_with_tools.content}")
        if response_with_tools.tool_calls:
            print(f"Tool calls: {response_with_tools.tool_calls}")
    else:
        print(f"Error: {response_with_tools.error}")

if __name__ == "__main__":
    main() 