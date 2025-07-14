#!/usr/bin/env python3
"""
Direct OpenAI API test for function calling
"""

import json
import os
import dotenv
from openai import AzureOpenAI

dotenv.load_dotenv()

def test_direct_openai():
    """Test function calling directly with OpenAI client"""
    
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-02-15-preview",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Simple tool definition
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location to get weather for"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    # Initial messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the weather in Paris?"}
    ]
    
    print("=== Round 1: Initial call ===")
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        print(f"Response: {response}")
        message = response.choices[0].message
        print(f"Message content: {message.content}")
        print(f"Tool calls: {message.tool_calls}")
        
        # Add assistant message
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ] if message.tool_calls else None
        })
        
        # Simulate tool execution and add tool message
        if message.tool_calls:
            for tc in message.tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": '{"weather": "sunny", "temperature": "20°C"}'
                })
        
        print("\n=== Messages after Round 1 ===")
        for i, msg in enumerate(messages):
            print(f"  {i}: {msg}")
        
        print("\n=== Round 2: Response to tool results ===")
        response2 = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        print(f"Round 2 success!")
        print(f"Round 2 content: {response2.choices[0].message.content}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_direct_openai() 