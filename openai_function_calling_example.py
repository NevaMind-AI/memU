#!/usr/bin/env python3
"""
OpenAI Official Function Calling Example

Demonstrates how to use Memory Agent following OpenAI best practices
"""

import json
from memu.llm import OpenAIClient
from memu.memory import MemoryAgent

def main():
    """OpenAI Function Calling Best Practices Example"""
    
    print("🚀 OpenAI Official Function Calling Example")
    print("=" * 50)
    
    # 1. Initialize components
    llm_client = OpenAIClient(model="gpt-4o-mini")
    memory_agent = MemoryAgent(llm_client=llm_client, memory_dir="memory")
    
    # 2. Get OpenAI-compatible function definitions
    function_schemas = memory_agent.get_functions_schema()
    
    print(f"📋 Available functions: {len(function_schemas)} functions")
    for schema in function_schemas:
        print(f"  • {schema['name']}: {schema['description']}")
    print()
    
    # 3. Build conversation - use clear instructions to trigger function calls
    messages = [
        {
            "role": "system",
            "content": """You are an intelligent assistant that can use memory functions to store and retrieve information.
            
When users ask you to remember information, use the add_memory function.
When users ask about previous information, use search_memory or read_memory functions.
When users ask to update information, use the update_memory function.

Please choose the appropriate function calls based on user needs."""
        },
        {
            "role": "user",
            "content": "Please help me remember: My name is Alice, I'm 25 years old, I'm a product manager, and I like reading and traveling."
        }
    ]
    
    # 4. Call following OpenAI official format
    def process_conversation(messages, max_iterations=5):
        """Process conversation with support for multiple function calls"""
        
        for iteration in range(max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}")
            print("-" * 20)
            
            # Call OpenAI API
            response = llm_client.chat_completion(
                messages=messages,
                tools=[{"type": "function", "function": schema} for schema in function_schemas],
                tool_choice="auto",
                temperature=0.3
            )
            
            if not response.success:
                print(f"❌ API call failed: {response.error}")
                break
            
            # Add assistant reply to conversation history
            assistant_message = {
                "role": "assistant",
                "content": response.content
            }
            
            # Handle function calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🛠️ Detected {len(response.tool_calls)} function calls")
                
                # Add function calls to assistant message
                assistant_message["tool_calls"] = response.tool_calls
                messages.append(assistant_message)
                
                # Execute each function call
                for tool_call in response.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    print(f"  📞 Calling: {function_name}")
                    print(f"  📝 Arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
                    
                    # Execute function
                    result = memory_agent.call_function(function_name, arguments)
                    
                    # Add tool result to conversation history
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    }
                    messages.append(tool_message)
                    
                    print(f"  ✅ Result: {'Success' if result.get('success') else 'Failed'}")
                    if result.get('success'):
                        if 'file_path' in result:
                            print(f"  📁 File: {result['file_path']}")
                    else:
                        print(f"  ❌ Error: {result.get('error')}")
                
            else:
                # No function calls, add reply and end
                messages.append(assistant_message)
                if response.content:
                    print(f"💬 Assistant reply: {response.content}")
                break
        
        return messages
    
    # 5. Process first conversation round
    print("💬 First conversation: Store information")
    messages = process_conversation(messages)
    
    # 6. Add new user message for testing
    print("\n" + "=" * 50)
    print("💬 Second conversation: Retrieve information")
    
    messages.append({
        "role": "user",
        "content": "What is Alice's profession? What are her hobbies?"
    })
    
    messages = process_conversation(messages)
    
    # 7. Demonstrate update functionality
    print("\n" + "=" * 50)
    print("💬 Third conversation: Update information")
    
    messages.append({
        "role": "user", 
        "content": "Alice is now 26 years old, please update her age information."
    })
    
    messages = process_conversation(messages)
    
    print("\n🎉 Example completed!")
    print("\n📋 Summary:")
    print("✅ Uses OpenAI official function calling format")
    print("✅ Supports multiple function calls")
    print("✅ Properly handles tool calls and results")
    print("✅ Maintains complete conversation history")
    print("✅ Follows OpenAI best practices")

if __name__ == "__main__":
    main() 