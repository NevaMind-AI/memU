#!/usr/bin/env python3
"""
RecallAgent Three Retrieval Methods Example

Demonstrates the new RecallAgent's three distinct retrieval methods:
Automatically scans {character_name}_{category}.md files in memory directory.

1. retrieve_default_category: Get content from ['profile', 'event'] categories
2. retrieve_relevant_category: Get top-k similar category names (excluding profile/event/activity)
3. retrieve_relevant_memories: Get top-k memories using embedding search
"""

import os
import sys
from pathlib import Path

# Add the memu package to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from memu.memory import RecallAgent


def demo_retrieve_default_category():
    """
    Demonstrate Method 1: retrieve_default_category()
    Gets complete content from ['profile', 'event'] categories
    """
    print("=== Method 1: retrieve_default_category() ===")
    print("Getting content from default categories: ['profile', 'event']")
    print("Scans for {character_name}_{category}.md files in memory directory\n")
    
    recall_agent = RecallAgent(memory_dir="memory")
    character_name = "Maria"
    
    result = recall_agent.retrieve_default_category(character_name)
    
    if result.get("success"):
        results = result.get('results', [])
        requested_categories = result.get('requested_categories', [])
        existing_categories = result.get('existing_categories', [])
        all_categories_found = result.get('all_categories_found', [])
        
        print(f"📁 All categories found in files: {all_categories_found}")
        print(f"🎯 Requested default categories: {requested_categories}")
        print(f"✅ Existing default files: {existing_categories}")
        print(f"📄 Retrieved {len(results)} default categories:")
        
        for i, item in enumerate(results, 1):
            category = item.get('category', 'unknown')
            length = item.get('length', 0)
            lines = item.get('lines', 0)
            content = item.get('content', '')
            file_exists = item.get('file_exists', False)
            
            print(f"\n  {i}. {category.upper()} {'✅' if file_exists else '❌'}")
            print(f"     📊 Length: {length} chars, {lines} lines")
            print(f"     📝 FULL CONTENT:")
            print("     " + "="*50)
            
            # Display full content with proper formatting
            content_lines = content.split('\n')
            for line_num, line in enumerate(content_lines, 1):
                print(f"     {line_num:3d}| {line}")
            
            print("     " + "="*50)
            print()
    else:
        print(f"❌ Failed: {result.get('error')}")


def demo_retrieve_relevant_category():
    """
    Demonstrate Method 2: retrieve_relevant_category()
    Gets top-k similar category names (excluding profile, event, and activity)
    """
    print("=== Method 2: retrieve_relevant_category() ===")
    print("Getting relevant categories based on query similarity")
    print("Scans for {character_name}_{category}.md files in memory directory")
    print("(Excludes: profile, event, activity)\n")
    
    recall_agent = RecallAgent(memory_dir="memory")
    character_name = "Maria"
    query = "cooking food family dinner"
    top_k = 3
    
    result = recall_agent.retrieve_relevant_category(character_name, query, top_k)
    
    if result.get("success"):
        results = result.get('results', [])
        all_categories_found = result.get('all_categories_found', [])
        excluded_categories = result.get('excluded_categories', [])
        available_categories = result.get('available_categories', [])
        
        print(f"🔍 Query: '{query}'")
        print(f"📁 All categories found in files: {all_categories_found}")
        print(f"❌ Excluded categories: {excluded_categories}")
        print(f"📋 Available for search: {available_categories}")
        print(f"✅ Retrieved top {len(results)} relevant categories:")
        
        for i, item in enumerate(results, 1):
            category = item.get('category', 'unknown')
            score = item.get('relevance_score', 0.0)
            exact_match = item.get('exact_match', False)
            word_overlap = item.get('word_overlap', 0.0)
            content_relevance = item.get('content_relevance', 0.0)
            length = item.get('length', 0)
            content = item.get('content', '')
            
            print(f"\n  {i}. {category.upper()} (score: {score:.3f})")
            print(f"     🎯 Exact match: {exact_match}")
            print(f"     📊 Word overlap: {word_overlap:.3f}")
            print(f"     📝 Content relevance: {content_relevance:.3f}")
            print(f"     📄 Length: {length} chars")
            print(f"     💬 FULL CONTENT:")
            print("     " + "="*50)
            
            # Display full content with proper formatting
            content_lines = content.split('\n')
            for line_num, line in enumerate(content_lines, 1):
                print(f"     {line_num:3d}| {line}")
            
            print("     " + "="*50)
            print()
    else:
        print(f"❌ Failed: {result.get('error')}")


def demo_retrieve_relevant_memories():
    """
    Demonstrate Method 3: retrieve_relevant_memories()
    Gets top-k memories using embedding search across all categories
    """
    print("=== Method 3: retrieve_relevant_memories() ===")
    print("Getting relevant memories using semantic search\n")
    
    recall_agent = RecallAgent(memory_dir="memory")
    character_name = "Maria"
    query = "outdoor activities hiking exercise"
    top_k = 5
    
    result = recall_agent.retrieve_relevant_memories(character_name, query, top_k)
    
    if result.get("success"):
        results = result.get('results', [])
        total_candidates = result.get('total_candidates', 0)
        
        print(f"🔍 Query: '{query}'")
        print(f"📊 Found {total_candidates} candidates, showing top {len(results)}:")
        
        for i, item in enumerate(results, 1):
            category = item.get('category', 'unknown')
            score = item.get('semantic_score', 0.0)
            length = item.get('length', 0)
            line_number = item.get('line_number', 0)
            content = item.get('content', '')
            item_id = item.get('item_id', '')
            memory_id = item.get('memory_id', '')
            
            print(f"\n  {i}. {category.upper()} (similarity: {score:.3f})")
            print(f"     📄 Length: {length} chars, Line: {line_number}")
            print(f"     🆔 Item ID: {item_id}")
            print(f"     🧠 Memory ID: {memory_id}")
            print(f"     💭 FULL MEMORY:")
            print("     " + "="*50)
            
            # Display full content
            print(f"     {content}")
            
            print("     " + "="*50)
            print()
    else:
        print(f"❌ Failed: {result.get('error')}")





def main():
    """Main demonstration function"""
    print("🌟 RecallAgent Three Retrieval Methods Demo")
    print("Testing the enhanced RecallAgent with three distinct methods\n")
    print("📌 NOTE: This demo shows FULL CONTENT of all retrieved items\n")
    
    try:
        # Check agent status first
        recall_agent = RecallAgent(memory_dir="memory")
        status = recall_agent.get_status()
        print(f"📊 Agent Status:")
        print(f"   Type: {status.get('agent_type')}")
        print(f"   Semantic Search: {'Enabled' if status.get('semantic_search_enabled') else 'Disabled'}")
        print(f"   Default Categories: {status.get('default_categories')}")
        print(f"   Available Methods: {len(status.get('retrieval_methods', []))}")
        print()
        
        # Ask user which demo to run
        print("Select which demo to run:")
        print("  1. retrieve_default_category (Method 1)")
        print("  2. retrieve_relevant_category (Method 2)")
        print("  3. retrieve_relevant_memories (Method 3)")
        
        try:
            choice = input("\nEnter your choice (1-3, default=1): ").strip()
            if not choice:
                choice = "1"
        except:
            choice = "1"
        
        print()
        
        if choice == "1":
            demo_retrieve_default_category()
        elif choice == "2":
            demo_retrieve_relevant_category()
        elif choice == "3":
            demo_retrieve_relevant_memories()
        else:
            demo_retrieve_default_category()
        
        print("\n✅ Demo completed successfully!")
        print("\n📚 Summary:")
        print("  1. retrieve_default_category: Fixed categories (profile, event) - scans actual files")
        print("  2. retrieve_relevant_category: Query-based category matching - scans {char}_{category}.md files")
        print("     (excludes profile/event/activity)")
        print("  3. retrieve_relevant_memories: Semantic embedding search")
        print("\n📌 Content shown above is the COMPLETE retrieved content!")
        print("📁 All methods now scan actual files in memory directory!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 