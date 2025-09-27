import os
import time

from memu import MemuClient


def print_chat_response(response, message_num: int):
    """Print chat response with detailed token usage."""
    print(f"\n🤖 Chat Response #{message_num}:")
    print(f"   {response.message}")
    
    print("\n📊 Token Usage:")
    usage = response.chat_token_usage
    print(f"   Total Tokens: {usage.total_tokens}")
    print(f"   Prompt Tokens: {usage.prompt_tokens}")
    print(f"   Completion Tokens: {usage.completion_tokens}")
    
    if usage.prompt_tokens_breakdown:
        breakdown = usage.prompt_tokens_breakdown
        print("   📈 Token Breakdown:")
        print(f"     - Current Query: {breakdown.current_query}")
        print(f"     - Short Term Context: {breakdown.short_term_context}")  
        print(f"     - User Profile: {breakdown.user_profile}")
        print(f"     - Retrieved Memory: {breakdown.retrieved_memory}")


def main():
    """Main chat demonstration function."""
    print("🚀 MemU Chat API Demo")
    print("=" * 50)
    
    # Initialize MemU client
    memu_client = MemuClient(
        base_url="https://api.memu.so", 
        api_key=os.getenv("MEMU_API_KEY")
    )
    
    user_id = "chat_demo_user"
    agent_id = "chat_demo_assistant"
    user_name = "Demo User"
    agent_name = "Chat Assistant"

    print("\n💬 Starting chat session...")
    print("-" * 50)

    # Chat examples demonstrating different scenarios
    chat_examples = [
        {
            "message": "Hello! Can you help me with some hiking advice?",
            "kwargs": {"temperature": 0.7, "max_tokens": 150},
            "description": "Basic chat with memory retrieval"
        },
        {
            "message": "I'm planning to cook Italian food tonight. What should I make?", 
            "kwargs": {"temperature": 0.8, "max_tokens": 200},
            "description": "Query related to pasta making from memory"
        },
        {
            "message": "I'm feeling overwhelmed at work and considering a career change. Any advice?",
            "kwargs": {"temperature": 0.6, "max_tokens": 180},
            "description": "Career advice drawing from previous conversation"
        },
        {
            "message": "What are some easy vegetables I can grow in my garden this spring?",
            "kwargs": {"temperature": 0.5, "max_tokens": 160},
            "description": "Gardening advice with memory context"
        },
        {
            "message": "I want to start learning a new language. What's the best approach?",
            "kwargs": {"temperature": 0.7, "max_tokens": 170},
            "description": "Language learning guidance"
        }
    ]

    # Conduct the chat session
    for i, example in enumerate(chat_examples, 1):
        print(f"\n👤 User Message #{i}: {example['message']}")
        print(f"   Context: {example['description']}")
        print(f"   LLM Parameters: {example['kwargs']}")
        
        try:
            # Send chat message
            response = memu_client.chat(
                user_id=user_id,
                user_name=user_name,
                agent_id=agent_id,
                agent_name=agent_name,
                message=example['message'],
                max_context_tokens=4000,
                **example['kwargs']
            )
            
            # Print detailed response
            print_chat_response(response, i)
            
        except Exception as e:
            print(f"   ❌ Chat error: {e}")
            
        # Small delay between messages
        time.sleep(1)

    # Close the client
    memu_client.close()
    
    print("\n✨ Chat API demo completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
