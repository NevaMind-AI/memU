#!/usr/bin/env python3
"""
Simple test script for function calling debugging
"""

import json
import os
import sys
import dotenv

dotenv.load_dotenv()

# Add PersonaLab to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from memory_agent_tools import MemoryAgentTools
from personalab.utils import setup_logging

logger = setup_logging(__name__, enable_flush=True)

def test_simple_function_calling():
    """Test basic function calling with detailed logging"""
    tools = MemoryAgentTools()
    
    # Get tools
    available_tools = tools.get_available_tools()
    print("Available tools:", len(available_tools))
    
    # Test messages format
    messages = [
        {
            "role": "system",
            "content": "You are a test assistant. Use the list_available_characters tool to list characters."
        },
        {
            "role": "user", 
            "content": "List available characters"
        }
    ]
    
    print("Initial messages:")
    for i, msg in enumerate(messages):
        print(f"  {i}: {msg}")
    
    # Call LLM with tools
    try:
        response = tools.llm_client.chat_completion(
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            max_tokens=1000
        )
        
        print("\nLLM Response:")
        print(f"  Success: {response.success}")
        print(f"  Content: {response.content}")
        print(f"  Tool calls: {response.tool_calls}")
        
        if response.tool_calls:
            for i, tc in enumerate(response.tool_calls):
                print(f"    Tool call {i}:")
                print(f"      ID: {tc.id}")
                print(f"      Type: {tc.type}")
                print(f"      Function name: {tc.function.name}")
                print(f"      Function args: {tc.function.arguments}")
                
                # Test tool execution
                try:
                    args = json.loads(tc.function.arguments)
                    tool_result = tools.execute_tool(tc.function.name, **args)
                    print(f"      Tool result: {tool_result}")
                except Exception as e:
                    print(f"      Tool execution error: {e}")
    
    except Exception as e:
        print(f"Error: {e}")

def test_complete_function_calling():
    """Test complete function calling conversation"""
    tools = MemoryAgentTools()
    available_tools = tools.get_available_tools()
    
    # Initial messages
    messages = [
        {
            "role": "system",
            "content": "You are a test assistant. Use the list_available_characters tool to list characters."
        },
        {
            "role": "user", 
            "content": "List available characters"
        }
    ]
    
    print("=== Round 1: Initial call ===")
    response = tools.llm_client.chat_completion(
        messages=messages,
        tools=available_tools,
        tool_choice="auto",
        max_tokens=1000
    )
    
    print(f"Response success: {response.success}")
    print(f"Tool calls: {len(response.tool_calls) if response.tool_calls else 0}")
    
    if response.tool_calls:
        # Add assistant message with tool_calls
        assistant_msg = {
            "role": "assistant",
            "content": response.content if response.content else None
        }
        
        # Add tool_calls in correct format
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in response.tool_calls
        ]
        
        messages.append(assistant_msg)
        
        # Process each tool call
        for tc in response.tool_calls:
            # Execute tool
            try:
                args = json.loads(tc.function.arguments)
                tool_result = tools.execute_tool(tc.function.name, **args)
                print(f"Tool result: {tool_result}")
                
                # Add tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result)
                })
                
            except Exception as e:
                print(f"Tool execution error: {e}")
                messages.append({
                    "role": "tool", 
                    "tool_call_id": tc.id,
                    "content": json.dumps({"success": False, "error": str(e)})
                })
        
        print("\n=== Messages after Round 1 ===")
        for i, msg in enumerate(messages):
            print(f"  {i}: {msg}")
        
        print("\n=== Round 2: Response to tool results ===")
        try:
            response2 = tools.llm_client.chat_completion(
                messages=messages,
                tools=available_tools,
                tool_choice="auto",
                max_tokens=1000
            )
            
            print(f"Round 2 success: {response2.success}")
            print(f"Round 2 content: {response2.content}")
            print(f"Round 2 tool calls: {len(response2.tool_calls) if response2.tool_calls else 0}")
            
        except Exception as e:
            print(f"Round 2 error: {e}")

if __name__ == "__main__":
    test_complete_function_calling() 