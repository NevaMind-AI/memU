"""
MemU Clean Architecture Example

This example demonstrates the new clean, modular agent architecture:
1. MetaAgent: Coordinates all specialized agents
2. Specialized Agents: Each handles one specific memory type
3. No legacy code: Simple, focused design

Architecture:
Raw Conversation → ActivityAgent → activity.md → Specialized Agents → Memory Files
"""

import os
from pathlib import Path
from datetime import datetime

# Import the new clean architecture
from memu import MetaAgent, create_agent, get_available_agents
from memu.llm import OpenAIClient, AnthropicClient


def setup_llm_client():
    """Setup LLM client based on available API keys"""
    if os.getenv('OPENAI_API_KEY'):
        return OpenAIClient()
    elif os.getenv('ANTHROPIC_API_KEY'):
        return AnthropicClient()
    else:
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        return None


def basic_usage_example():
    """Basic usage of the MetaAgent with specialized agents"""
    print("=== Basic Usage Example ===\n")
    
    # Setup LLM client
    llm_client = setup_llm_client()
    if not llm_client:
        return
    
    # Create MetaAgent (coordinates all specialized agents)
    meta_agent = MetaAgent(
        llm_client=llm_client,
        memory_dir="example_memory",
        use_database=False  # Use file storage for this example
    )
    
    print(f"✅ MetaAgent created with agents: {meta_agent.agent_names}")
    
    # Process a conversation
    test_conversation = """
    Hi! I'm Alice, a 28-year-old software engineer from San Francisco. 
    I love hiking and just started learning piano. I'm working on a machine learning project 
    and need to finish the presentation by Friday. I also want to remember to call my mom tomorrow.
    """
    
    print("🚀 Processing conversation...")
    results = meta_agent.process_conversation(
        conversation=test_conversation,
        character_name="Alice",
        session_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    if results["success"]:
        print("✅ Conversation processed successfully!")
        print(f"📝 Activity summary: {results['activity_summary'][:100]}...")
        print(f"🔧 Agents executed: {list(results['agent_outputs'].keys())}")
        
        if results.get("errors"):
            print(f"⚠️ Some errors: {results['errors']}")
    else:
        print(f"❌ Processing failed: {results.get('errors')}")


def individual_agent_example():
    """Example of working with individual specialized agents"""
    print("\n=== Individual Agent Example ===\n")
    
    llm_client = setup_llm_client()
    if not llm_client:
        return
    
    # Show available agent types
    available_agents = get_available_agents()
    print(f"📋 Available agent types: {available_agents}")
    
    # Create individual agents
    print("\n🧠 Creating individual agents:")
    
    activity_agent = create_agent(
        "activity_agent",
        llm_client=llm_client,
        memory_dir="example_memory",
        use_database=False
    )
    print(f"✅ ActivityAgent: {activity_agent}")
    
    profile_agent = create_agent(
        "profile_agent", 
        llm_client=llm_client,
        memory_dir="example_memory",
        use_database=False
    )
    print(f"✅ ProfileAgent: {profile_agent}")
    
    # Show agent properties
    print(f"\n📊 Agent Properties:")
    print(f"Activity Agent - Type: {activity_agent.memory_type}, Priority: {activity_agent.get_priority()}")
    print(f"Profile Agent - Type: {profile_agent.memory_type}, Priority: {profile_agent.get_priority()}")


def memory_operations_example():
    """Example of memory read/write operations"""
    print("\n=== Memory Operations Example ===\n")
    
    llm_client = setup_llm_client()
    if not llm_client:
        return
    
    meta_agent = MetaAgent(
        llm_client=llm_client,
        memory_dir="example_memory",
        use_database=False
    )
    
    character_name = "Alice"
    
    # Read existing memories
    print("📖 Reading existing memories:")
    memories = meta_agent.read_character_memory(character_name)
    
    for memory_type, content in memories.items():
        if content.strip():
            print(f"✅ {memory_type}: {len(content)} characters")
        else:
            print(f"📄 {memory_type}: (empty)")
    
    # Search memories
    if any(content.strip() for content in memories.values()):
        print("\n🔍 Searching memories:")
        search_results = meta_agent.search_character_memories(
            character_name=character_name,
            query="piano learning music",
            limit=3
        )
        print(f"Found {len(search_results)} relevant memories")
    
    # Get agent status
    print("\n📊 Agent Status:")
    status = meta_agent.get_agent_status()
    print(f"Total agents: {status['total_agents']}")
    print(f"Loaded agents: {status['loaded_agents']}")


def database_mode_example():
    """Example using database storage with vectors"""
    print("\n=== Database Mode Example ===\n")
    
    llm_client = setup_llm_client()
    if not llm_client:
        return
    
    try:
        # Try to create MetaAgent with database storage
        meta_agent = MetaAgent(
            llm_client=llm_client,
            use_database=True,  # Use database storage
            # Database connection will use environment variables
        )
        
        print("✅ Database mode MetaAgent created successfully")
        print("🔍 This mode supports vector similarity search")
        
        # Process a conversation
        conversation = "I really enjoy classical music and I'm learning to play Chopin pieces on piano."
        
        results = meta_agent.process_conversation(
            conversation=conversation,
            character_name="MusicLover",
            session_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        if results["success"]:
            print("✅ Conversation processed with database storage")
            print("🔍 Vector embeddings generated for semantic search")
        
    except Exception as e:
        print(f"⚠️ Database mode not available: {e}")
        print("💡 Make sure PostgreSQL is configured and accessible")


def cleanup_example_files():
    """Clean up example memory files"""
    print("\n🧹 Cleaning up example files...")
    import shutil
    
    example_dir = Path("example_memory")
    if example_dir.exists():
        shutil.rmtree(example_dir)
        print("✅ Example files cleaned up")


def main():
    """Run all examples"""
    print("🧪 MemU Clean Architecture Examples")
    print("=" * 50)
    
    # Run examples
    basic_usage_example()
    individual_agent_example()
    memory_operations_example()
    database_mode_example()
    
    # Cleanup
    cleanup_example_files()
    
    print("\n" + "=" * 50)
    print("🎉 All examples completed!")
    print("\n💡 Key Benefits of New Architecture:")
    print("   ✅ True modularity - each agent is independent")
    print("   ✅ Easy extension - add new agent types easily")
    print("   ✅ Better performance - agents can run in parallel")
    print("   ✅ Clean separation - each agent handles one memory type")
    print("   ✅ No legacy code - simple, focused design")


if __name__ == "__main__":
    main() 