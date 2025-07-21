#!/usr/bin/env python3
"""
Intelligent Memory Agent Usage Example - Structured Workflow

Demonstrates Memory Agent's new structured workflow:
1. Summarize conversation → Extract distinct memory items
2. Store memory items and summary to activity
3. Get available categories
4. Generate memory suggestions
5. Update each category based on suggestions (returns structured format)
6. Link related memories
"""

import asyncio
from memu.llm import OpenAIClient, AnthropicClient
from memu.memory import MemoryAgent
import json

async def demo_memory_workflow():
    """Demonstrate complete memory workflow"""
    
    print("🧠 Intelligent Memory Agent Workflow Demo")
    print("=" * 50)
    
    # Initialize LLM client (choose one)
    # llm_client = OpenAIClient(model="gpt-4o-mini")
    llm_client = AnthropicClient(model="claude-3-5-haiku-20241022")
    
    # Initialize memory agent
    memory_agent = MemoryAgent(llm_client=llm_client, memory_dir="memory")
    character_name = "Alice"
    
    # Simulate conversation content
    conversation = """
    User: Hi Alice! How was your weekend?
    Alice: It was great! I went hiking in the mountains with my friend Sarah. We discovered a beautiful waterfall and took lots of photos. I also finished reading "The Midnight Library" by Matt Haig - such an inspiring book about life choices and possibilities.
    
    User: That sounds wonderful! What did you think of the book?
    Alice: I loved it! It really made me think about different paths in life. I've been feeling a bit stuck in my current job as a product manager, and the book reminded me that it's never too late to make changes. I'm actually considering taking a photography course since I enjoyed capturing those nature shots so much.
    
    User: Have you always been interested in photography?
    Alice: I used to love it in college, but I put it aside when I got busy with my career. Seeing those mountain views this weekend rekindled my passion. I'm thinking about joining a local photography club to improve my skills and meet like-minded people.
    """
    
    print(f"📖 Original conversation:")
    print(conversation)
    print("\n" + "=" * 50)
    
    # Step 1: Summarize conversation and extract memory items
    print("🔍 Step 1: Summarizing conversation and extracting memory items...")
    conversation_result = await memory_agent.summarize_conversation(
        conversation=conversation,
        character_name=character_name,
        session_date="2024-01-15"
    )
    
    if conversation_result.success:
        print("✅ Conversation summary successful")
        print(f"📝 Summary: {conversation_result.data['summary'][:200]}...")
        print(f"📊 Extracted {len(conversation_result.data['memory_items'])} memory items")
        for i, item in enumerate(conversation_result.data['memory_items'][:3], 1):
            print(f"  {i}. {item[:100]}...")
    else:
        print(f"❌ Conversation summary failed: {conversation_result.error}")
        return
    
    print("\n" + "-" * 30)
    
    # Step 2: Get available categories
    print("📋 Step 2: Getting available memory categories...")
    categories_result = await memory_agent.get_available_categories(character_name)
    
    if categories_result.success:
        categories = categories_result.data
        print(f"✅ Found {len(categories)} categories: {list(categories.keys())}")
        for cat, info in categories.items():
            print(f"  📁 {cat}: {info['description']}")
    else:
        print(f"❌ Failed to get categories: {categories_result.error}")
        return
    
    print("\n" + "-" * 30)
    
    # Step 3: Generate memory suggestions
    print("💡 Step 3: Generating memory update suggestions...")
    suggestions_result = await memory_agent.generate_suggestions(
        memory_items=conversation_result.data['memory_items'],
        character_name=character_name,
        available_categories=categories
    )
    
    if suggestions_result.success:
        suggestions = suggestions_result.data
        print("✅ Memory suggestions generated successfully")
        for category, suggestion_data in suggestions.items():
            should_add = suggestion_data.get('should_add', False)
            status = "📈 ADD" if should_add else "⏸️ SKIP"
            print(f"  {status} {category}: {suggestion_data.get('summary', 'No summary')[:100]}...")
    else:
        print(f"❌ Failed to generate suggestions: {suggestions_result.error}")
        return
    
    print("\n" + "-" * 30)
    
    # Step 4: Update memories based on suggestions
    print("🔄 Step 4: Updating memories based on suggestions...")
    update_result = await memory_agent.update_memory_with_suggestions(
        suggestions=suggestions,
        character_name=character_name,
        session_date="2024-01-15"
    )
    
    if update_result.success:
        update_data = update_result.data
        print("✅ Memory update completed")
        print(f"📊 Updated categories: {len(update_data['updated_categories'])}")
        
        for category in update_data['updated_categories']:
            if category in update_data['results']:
                result = update_data['results'][category]
                status = "✅" if result['success'] else "❌"
                print(f"  {status} {category}: {result.get('message', 'No message')}")
                if result['success'] and 'file_path' in result:
                    print(f"    📁 File: {result['file_path']}")
        
        if update_data['skipped_categories']:
            print(f"⏸️ Skipped categories: {', '.join(update_data['skipped_categories'])}")
    else:
        print(f"❌ Memory update failed: {update_result.error}")
        return
    
    print("\n" + "-" * 30)
    
    # Step 5: Link related memories
    print("🔗 Step 5: Linking related memories...")
    link_result = await memory_agent.link_related_memories(
        character_name=character_name,
        memory_items=conversation_result.data['memory_items']
    )
    
    if link_result.success:
        print("✅ Memory linking completed")
        link_data = link_result.data
        if link_data.get('links_created', 0) > 0:
            print(f"🔗 Created {link_data['links_created']} new memory links")
            for link in link_data.get('new_links', [])[:3]:
                print(f"  • {link[:100]}...")
        else:
            print("ℹ️ No new memory links needed")
    else:
        print(f"❌ Memory linking failed: {link_result.error}")
    
    print("\n" + "=" * 50)
    print("🎉 Memory workflow completed successfully!")
    
    # Step 6: Demonstrate memory retrieval
    print("\n🔍 Step 6: Demonstrating memory retrieval...")
    search_result = await memory_agent.search_memory(
        query="photography interests hobbies",
        character_name=character_name,
        top_k=3
    )
    
    if search_result.success:
        results = search_result.data
        print(f"📖 Found {len(results)} relevant memories:")
        for i, result in enumerate(results[:2], 1):
            print(f"  {i}. {result['content'][:150]}...")
            print(f"     📁 Source: {result['metadata']['file_type']} (Score: {result['score']:.3f})")
    else:
        print(f"❌ Memory search failed: {search_result.error}")

if __name__ == "__main__":
    asyncio.run(demo_memory_workflow()) 