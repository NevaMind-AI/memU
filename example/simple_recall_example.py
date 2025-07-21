#!/usr/bin/env python3
"""
Simple Recall Agent Usage Example

Demonstrates how to use RecallAgent to search and retrieve memories:
1. Initialize RecallAgent with memory directory
2. Perform various types of searches (full context and RAG)
3. Display search results with scores and relevance
4. Show the difference between context=all and context=rag content

This example uses the pre-existing Alice memory files in the example/memory directory.
"""

import os
import sys
from pathlib import Path

# Add the memu package to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from memu.memory import RecallAgent
import json
from datetime import datetime

def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80)

def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n📋 {title}")
    print("-" * 50)

def display_full_context_results(full_context: list):
    """Display full context content in an organized way"""
    if not full_context:
        print("   ❌ No full context content found")
        return
    
    print(f"   ✅ Found {len(full_context)} full context categories:")
    
    for i, item in enumerate(full_context, 1):
        category = item.get('category', 'unknown')
        content = item.get('content', '')
        length = item.get('length', 0)
        lines = item.get('lines', 0)
        
        print(f"\n   {i}. Category: {category.upper()}")
        print(f"      📊 Content length: {length} characters, {lines} lines")
        print(f"      📝 Content preview:")
        
        # Show first few lines of content
        content_lines = content.split('\n')
        preview_lines = content_lines[:3]
        for line in preview_lines:
            if line.strip():
                print(f"         {line[:100]}{'...' if len(line) > 100 else ''}")
        
        if len(content_lines) > 3:
            print(f"         ... and {len(content_lines) - 3} more lines")

def display_rag_results(rag_results: list):
    """Display RAG search results with scores and relevance"""
    if not rag_results:
        print("   ❌ No RAG search results found")
        return
    
    print(f"   ✅ Found {len(rag_results)} RAG search results:")
    
    for i, result in enumerate(rag_results, 1):
        category = result.get('category', 'unknown')
        character = result.get('character', 'unknown')
        content = result.get('content', '')
        combined_score = result.get('combined_score', 0.0)
        semantic_score = result.get('semantic_score', 0.0)
        bm25_score = result.get('bm25_score', 0.0)
        string_score = result.get('string_score', 0.0)
        exact_match = result.get('exact_match', False)
        relevance = result.get('relevance', 'unknown')
        methods_used = result.get('search_methods_used', [])
        
        print(f"\n   {i}. [{relevance.upper()}] {character} - {category.upper()}")
        print(f"      🎯 Combined Score: {combined_score:.3f}")
        print(f"      📊 Semantic: {semantic_score:.3f} | BM25: {bm25_score:.3f} | String: {string_score:.3f}")
        print(f"      🔍 Methods: {', '.join(methods_used)}")
        if exact_match:
            print(f"      ✅ Exact match found!")
        
        print(f"      📝 Content preview:")
        content_preview = content[:200] + "..." if len(content) > 200 else content
        print(f"         {content_preview}")

def format_full_context_results(full_context: list) -> str:
    """Format full context content as a string"""
    if not full_context:
        return "   ❌ No full context content found\n"
    
    result = f"   ✅ Found {len(full_context)} full context categories:\n"
    
    for i, item in enumerate(full_context, 1):
        category = item.get('category', 'unknown')
        content = item.get('content', '')
        length = item.get('length', 0)
        lines = item.get('lines', 0)
        
        result += f"\n   {i}. Category: {category.upper()}\n"
        result += f"      📊 Content length: {length} characters, {lines} lines\n"
        result += f"      📝 Content preview:\n"
        
        # Show first few lines of content
        content_lines = content.split('\n')
        preview_lines = content_lines[:3]
        for line in preview_lines:
            if line.strip():
                line_preview = line[:100] + "..." if len(line) > 100 else line
                result += f"         {line_preview}\n"
        
        if len(content_lines) > 3:
            result += f"         ... and {len(content_lines) - 3} more lines\n"
    
    return result

def format_rag_results(rag_results: list) -> str:
    """Format RAG search results as a string"""
    if not rag_results:
        return "   ❌ No RAG search results found\n"
    
    result = f"   ✅ Found {len(rag_results)} RAG search results:\n"
    
    for i, res in enumerate(rag_results, 1):
        category = res.get('category', 'unknown')
        character = res.get('character', 'unknown')
        content = res.get('content', '')
        combined_score = res.get('combined_score', 0.0)
        semantic_score = res.get('semantic_score', 0.0)
        bm25_score = res.get('bm25_score', 0.0)
        string_score = res.get('string_score', 0.0)
        exact_match = res.get('exact_match', False)
        relevance = res.get('relevance', 'unknown')
        methods_used = res.get('search_methods_used', [])
        
        result += f"\n   {i}. [{relevance.upper()}] {character} - {category.upper()}\n"
        result += f"      🎯 Combined Score: {combined_score:.3f}\n"
        result += f"      📊 Semantic: {semantic_score:.3f} | BM25: {bm25_score:.3f} | String: {string_score:.3f}\n"
        result += f"      🔍 Methods: {', '.join(methods_used)}\n"
        if exact_match:
            result += f"      ✅ Exact match found!\n"
        
        result += f"      📝 Content preview:\n"
        content_preview = content[:200] + "..." if len(content) > 200 else content
        result += f"         {content_preview}\n"
    
    return result

def get_full_recall_result(character_name: str, query: str, memory_dir: str = "example/memory", max_results: int = 10) -> str:
    """
    Get comprehensive recall results as a combined string
    
    Args:
        character_name: Name of the character to search for
        query: Search query
        memory_dir: Directory containing memory files
        max_results: Maximum number of RAG results to return
        
    Returns:
        Formatted string containing all recall results
    """
    # Initialize RecallAgent
    recall_agent = RecallAgent(memory_dir=memory_dir)
    
    # Get agent status
    status = recall_agent.get_status()
    
    # Perform search
    result = recall_agent.search(
        character_name=character_name,
        query=query,
        max_results=max_results,
        rag=True
    )
    
    # Format the complete result
    output = []
    output.append("=" * 80)
    output.append(f"🔍 RECALL RESULTS FOR: {character_name}")
    output.append("=" * 80)
    output.append(f"🔍 Query: '{query}'")
    output.append(f"🤖 Memory Directory: {memory_dir}")
    output.append(f"📊 Semantic Search: {'✅ Enabled' if status.get('semantic_search_enabled') else '❌ Disabled'}")
    
    if result.get("success"):
        output.append(f"✅ Search completed successfully")
        output.append(f"📊 Total full context items: {result.get('total_full_context', 0)}")
        output.append(f"📊 Total RAG results: {result.get('total_rag_results', 0)}")
        
        # Configuration info
        config_info = result.get('config_info', {})
        output.append(f"📋 Context=all types: {config_info.get('all_context_types', [])}")
        output.append(f"📋 Context=rag types: {config_info.get('rag_context_types', [])}")
        
        # Full context content
        output.append("\n" + "=" * 50)
        output.append("📋 FULL CONTEXT CONTENT (context=all)")
        output.append("=" * 50)
        output.append(format_full_context_results(result.get('full_context_content', [])))
        
        # RAG search results
        output.append("\n" + "=" * 50)
        output.append("📋 RAG SEARCH RESULTS (context=rag)")
        output.append("=" * 50)
        output.append(format_rag_results(result.get('rag_search_results', [])))
        
        # Analysis summary
        rag_results = result.get('rag_search_results', [])
        if rag_results:
            output.append("\n" + "=" * 50)
            output.append("📊 SEARCH ANALYSIS")
            output.append("=" * 50)
            
            # Method analysis
            method_counts = {}
            score_ranges = {'high': 0, 'medium': 0, 'low': 0}
            
            for res in rag_results:
                methods = res.get('search_methods_used', [])
                relevance = res.get('relevance', 'unknown')
                
                if relevance in score_ranges:
                    score_ranges[relevance] += 1
                
                for method in methods:
                    method_counts[method] = method_counts.get(method, 0) + 1
            
            output.append("📊 Search methods used:")
            for method, count in method_counts.items():
                output.append(f"   {method}: {count} results")
            
            output.append("\n📈 Relevance distribution:")
            for relevance, count in score_ranges.items():
                output.append(f"   {relevance}: {count} results")
        
        output.append("\n" + "=" * 80)
        output.append("🎉 RECALL COMPLETE")
        output.append("=" * 80)
        
    else:
        output.append(f"❌ Search failed: {result.get('error')}")
    
    return "\n".join(output)

def demo_basic_recall():
    """Demonstrate basic recall functionality"""
    print_section_header("BASIC RECALL DEMONSTRATION")
    
    # Initialize RecallAgent with the example memory directory
    memory_dir = "memory"
    recall_agent = RecallAgent(memory_dir=memory_dir)
    
    print(f"🤖 RecallAgent initialized with memory directory: {memory_dir}")
    
    # Check agent status
    status = recall_agent.get_status()
    print("\n📊 Agent Status:")
    print(f"   Agent Type: {status.get('agent_type', 'unknown')}")
    print(f"   Memory Types: {status.get('memory_types', [])}")
    print(f"   Semantic Search: {'✅ Enabled' if status.get('semantic_search_enabled') else '❌ Disabled'}")
    
    return recall_agent

def demo_search_scenarios(recall_agent):
    """Demonstrate different search scenarios"""
    print_section_header("SEARCH SCENARIOS")
    
    character_name = "Alice"
    
    # Scenario 1: Search about hiking
    print_subsection("Scenario 1: Search about hiking activities")
    query1 = "hiking mountains weekend"
    print(f"🔍 Query: '{query1}'")
    
    result1 = recall_agent.search(
        character_name=character_name,
        query=query1,
        max_results=5,
        rag=True
    )
    
    if result1.get("success"):
        print(f"✅ Search completed successfully")
        print(f"📊 Total full context items: {result1.get('total_full_context', 0)}")
        print(f"📊 Total RAG results: {result1.get('total_rag_results', 0)}")
        
        # Display full context
        print_subsection("Full Context Content (context=all)")
        display_full_context_results(result1.get('full_context_content', []))
        
        # Display RAG results
        print_subsection("RAG Search Results (context=rag)")
        display_rag_results(result1.get('rag_search_results', []))
    else:
        print(f"❌ Search failed: {result1.get('error')}")
    
    # Scenario 2: Search about photography
    print_subsection("Scenario 2: Search about photography interests")
    query2 = "photography course arts college"
    print(f"🔍 Query: '{query2}'")
    
    result2 = recall_agent.search(
        character_name=character_name,
        query=query2,
        max_results=3,
        rag=True
    )
    
    if result2.get("success"):
        print(f"✅ Search completed successfully")
        print(f"📊 Total RAG results: {result2.get('total_rag_results', 0)}")
        display_rag_results(result2.get('rag_search_results', []))
    else:
        print(f"❌ Search failed: {result2.get('error')}")
    
    # Scenario 3: Search with exact text match
    print_subsection("Scenario 3: Exact text search")
    query3 = "TechFlow Solutions"
    print(f"🔍 Query: '{query3}' (testing exact match)")
    
    result3 = recall_agent.search(
        character_name=character_name,
        query=query3,
        max_results=5,
        rag=True
    )
    
    if result3.get("success"):
        print(f"✅ Search completed successfully")
        display_rag_results(result3.get('rag_search_results', []))
    else:
        print(f"❌ Search failed: {result3.get('error')}")

def demo_context_comparison(recall_agent):
    """Demonstrate the difference between RAG and full context"""
    print_section_header("CONTEXT COMPARISON: RAG vs FULL CONTEXT")
    
    character_name = "Alice"
    query = "career work job"
    
    # Search with RAG enabled
    print_subsection("Search with RAG Enabled")
    print(f"🔍 Query: '{query}' (rag=True)")
    
    result_with_rag = recall_agent.search(
        character_name=character_name,
        query=query,
        max_results=10,
        rag=True
    )
    
    if result_with_rag.get("success"):
        print(f"✅ Full context items: {result_with_rag.get('total_full_context', 0)}")
        print(f"✅ RAG search results: {result_with_rag.get('total_rag_results', 0)}")
        
        # Show config information
        config_info = result_with_rag.get('config_info', {})
        print(f"📋 Context=all types: {config_info.get('all_context_types', [])}")
        print(f"📋 Context=rag types: {config_info.get('rag_context_types', [])}")
    
    # Search with RAG disabled
    print_subsection("Search with RAG Disabled")
    print(f"🔍 Query: '{query}' (rag=False)")
    
    result_no_rag = recall_agent.search(
        character_name=character_name,
        query=query,
        max_results=10,
        rag=False
    )
    
    if result_no_rag.get("success"):
        print(f"✅ Full context items: {result_no_rag.get('total_full_context', 0)}")
        print(f"⏸️ RAG search: Disabled")
        print(f"📊 Message: {result_no_rag.get('message')}")
        
        # Display only full context
        display_full_context_results(result_no_rag.get('full_context_content', []))

def demo_detailed_analysis(recall_agent):
    """Demonstrate detailed analysis of search results"""
    print_section_header("DETAILED SEARCH ANALYSIS")
    
    character_name = "Alice"
    query = "book reading library"
    
    print(f"🔍 Detailed analysis for query: '{query}'")
    
    result = recall_agent.search(
        character_name=character_name,
        query=query,
        max_results=10,
        rag=True
    )
    
    if not result.get("success"):
        print(f"❌ Search failed: {result.get('error')}")
        return
    
    print(f"✅ Search completed successfully")
    
    # Analyze configuration
    config_info = result.get('config_info', {})
    print_subsection("Configuration Analysis")
    print(f"📁 Full context types: {config_info.get('all_context_types', [])}")
    print(f"🔍 RAG search types: {config_info.get('rag_context_types', [])}")
    
    rag_length_configs = config_info.get('rag_length_configs', {})
    if rag_length_configs:
        print("📏 RAG length limitations:")
        for file_type, rag_length in rag_length_configs.items():
            limit_desc = "unlimited" if rag_length == -1 else f"{rag_length} lines"
            print(f"   {file_type}: {limit_desc}")
    
    # Analyze search results by method
    rag_results = result.get('rag_search_results', [])
    if rag_results:
        print_subsection("Search Method Analysis")
        
        method_counts = {}
        score_ranges = {'high': 0, 'medium': 0, 'low': 0}
        
        for res in rag_results:
            methods = res.get('search_methods_used', [])
            relevance = res.get('relevance', 'unknown')
            
            if relevance in score_ranges:
                score_ranges[relevance] += 1
            
            for method in methods:
                method_counts[method] = method_counts.get(method, 0) + 1
        
        print("📊 Search methods used:")
        for method, count in method_counts.items():
            print(f"   {method}: {count} results")
        
        print("📈 Relevance distribution:")
        for relevance, count in score_ranges.items():
            print(f"   {relevance}: {count} results")
    
    # Show best results
    print_subsection("Top Results")
    display_rag_results(rag_results[:3])

def main():
    """Main demonstration function"""
    print("🌟 SIMPLE RECALL AGENT DEMONSTRATION")
    print("This demo shows how to search and retrieve memories using RecallAgent")
    print("Using pre-existing Alice memory files from memory/\n")
    
    try:
        # Initialize and demonstrate basic functionality
        recall_agent = demo_basic_recall()
        
        # Run different search scenarios
        demo_search_scenarios(recall_agent)
        
        # Compare RAG vs full context
        demo_context_comparison(recall_agent)
        
        # Detailed analysis
        demo_detailed_analysis(recall_agent)
        
        print_section_header("DEMONSTRATION COMPLETE")
        print("🎉 Successfully demonstrated RecallAgent functionality!")
        print("📚 Key takeaways:")
        print("   • RecallAgent supports both full context and RAG search")
        print("   • Multiple search methods: semantic, BM25, and string matching")
        print("   • Results are scored and ranked by relevance")
        print("   • Configuration controls context=all vs context=rag behavior")
        print("   • Deduplication prevents overlap between full and RAG content")
        
        # Demonstrate the string-returning function
        print_section_header("STRING RESULT DEMONSTRATION")
        print("📝 Demonstrating get_full_recall_result() function that returns a combined string:")
        
        # Get recall result as string
        recall_string = get_full_recall_result(
            character_name="Alice",
            query="photography hiking weekend",
            memory_dir="example/memory",
            max_results=5
        )
        
        print("\n🎯 Result returned as string (first 500 characters):")
        print("-" * 60)
        print(recall_string[:500] + "..." if len(recall_string) > 500 else recall_string)
        print("-" * 60)
        print(f"📊 Total string length: {len(recall_string)} characters")
        print("✅ Full recall result successfully returned as combined string!")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

def demo_string_recall():
    """Demonstrate how to get recall results as a string"""
    print("🌟 STRING RECALL DEMONSTRATION")
    print("This shows how to get comprehensive recall results as a single string")
    
    # Example usage
    result_string = get_full_recall_result(
        character_name="Alice",
        query="hiking mountains photography",
        memory_dir="example/memory",
        max_results=10
    )
    
    print(f"\n📝 Retrieved {len(result_string)} characters of formatted recall data")
    print("=" * 80)
    print(result_string)
    print("=" * 80)
    
    return result_string

if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--string-only":
        # Run only the string demonstration
        demo_string_recall()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        # Show usage examples
        print("🌟 SIMPLE RECALL EXAMPLE USAGE")
        print("=" * 50)
        print("1. Full demo (default):        python simple_recall_example.py")
        print("2. String result only:        python simple_recall_example.py --string-only")
        print("3. Help:                      python simple_recall_example.py --help")
        print("\n📋 PROGRAMMATIC USAGE:")
        print("from simple_recall_example import get_full_recall_result")
        print()
        print("# Get recall results as a formatted string")
        print("result = get_full_recall_result(")
        print("    character_name='Alice',")
        print("    query='hiking mountains',")
        print("    memory_dir='example/memory',")
        print("    max_results=10")
        print(")")
        print("print(result)  # Prints comprehensive formatted recall results")
        print()
        print("📝 FUNCTION PARAMETERS:")
        print("  character_name (str): Name of character to search for")
        print("  query (str): Search query")
        print("  memory_dir (str): Path to memory directory (default: 'example/memory')")
        print("  max_results (int): Max RAG results to return (default: 10)")
        print()
        print("🎯 RETURNS: Formatted string with full context + RAG results + analysis")
    else:
        # Run the full demonstration
        main() 