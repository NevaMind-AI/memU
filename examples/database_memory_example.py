#!/usr/bin/env python3
"""
Example: Using Database Storage with PostgreSQL + pgvector

This example demonstrates how to use the new database storage features:
- Store character profiles and events in PostgreSQL
- Automatic embedding generation and storage
- Vector similarity search capabilities
- Comparison between file and database storage modes
"""

import sys
from pathlib import Path

# Add parent directory to path to import memu
sys.path.insert(0, str(Path(__file__).parent.parent))

from memu import MemoryAgent, MemoryDatabaseManager, EmbeddingClient, create_embedding_client
from memu.llm import OpenAIClient

def example_database_storage():
    """Example of using database storage directly"""
    print("=== Direct Database Storage Example ===")
    
    # Create database manager
    db_manager = MemoryDatabaseManager()
    
    # Optionally set up embedding client for vector generation
    try:
        embedding_client = create_embedding_client('openai')
        db_manager.set_embedding_client(embedding_client)
        print("✓ Embedding client configured for vector generation")
    except Exception as e:
        print(f"⚠ Embedding client not configured: {e}")
        print("  Vectors will not be generated")
    
    # Create test character data
    character_name = "Alice"
    
    profile_content = """# Alice's Profile

- **Name**: Alice Chen
- **Age**: 28  
- **Occupation**: Senior Software Engineer
- **Location**: San Francisco, CA
- **Education**: Computer Science, Stanford University
- **Specialties**: Full-stack development, machine learning, system design
- **Personality**: Analytical, curious, collaborative, detail-oriented
- **Interests**: AI research, hiking, photography, cooking
- **Goals**: Leading technical projects, mentoring junior developers
"""

    events_content = """# Alice's Recent Events

**2024-01-15**: Led architecture review for new microservices platform. Discussed scalability requirements and database design patterns.

**2024-01-16**: Mentored junior developer on debugging techniques and code optimization. Helped resolve performance issue in API endpoint.

**2024-01-17**: Attended AI/ML conference presentation on transformer architectures. Took notes on potential applications for current projects.

**2024-01-18**: Collaborated with product team on user story refinement. Provided technical feasibility assessment for new features.

**2024-01-19**: Completed code review for authentication service. Suggested improvements for security and error handling.
"""
    
    # Store data in database
    print(f"\nStoring data for {character_name}...")
    
    profile_success = db_manager.write_profile(character_name, profile_content)
    events_success = db_manager.write_events(character_name, events_content)
    
    if profile_success and events_success:
        print("✓ Character data stored successfully in database")
    else:
        print("✗ Failed to store character data")
        return
    
    # Retrieve data from database
    print(f"\nRetrieving data for {character_name}...")
    
    stored_profile = db_manager.read_profile(character_name)
    stored_events = db_manager.read_events(character_name)
    
    print(f"✓ Profile: {len(stored_profile)} characters")
    print(f"✓ Events: {len(stored_events)} characters")
    
    # Get character information
    char_info = db_manager.get_character_info(character_name)
    print(f"\n📊 Character Information:")
    print(f"   - Exists: {char_info.get('exists', False)}")
    print(f"   - Created: {char_info.get('created_at', 'Unknown')}")
    print(f"   - Updated: {char_info.get('updated_at', 'Unknown')}")
    
    content_info = char_info.get('content', {})
    for content_type, info in content_info.items():
        print(f"   - {content_type.title()}: {info['length']} chars, embedding: {info['has_embedding']}")

def example_vector_search():
    """Example of vector similarity search"""
    print("\n=== Vector Similarity Search Example ===")
    
    db_manager = MemoryDatabaseManager()
    
    # Set up embedding client
    try:
        embedding_client = create_embedding_client('openai')
        db_manager.set_embedding_client(embedding_client)
        print("✓ Embedding client ready for vector search")
    except Exception:
        print("⚠ No embedding client - vector search not available")
        return
    
    # Example search queries
    search_queries = [
        "software engineering and programming",
        "leadership and mentoring",
        "artificial intelligence and machine learning",
        "technical architecture and design"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")
        
        results = db_manager.search_similar_content(
            query=query,
            limit=3
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['character_name']} ({result['content_type']})")
                print(f"      Similarity: {result['similarity_score']:.3f}")
                print(f"      Content: {result['content'][:80]}...")
        else:
            print("   No similar content found")

def example_memory_agent_database():
    """Example of MemoryAgent with database backend"""
    print("\n=== MemoryAgent with Database Backend ===")
    
    # Create MemoryAgent with database storage
    agent = MemoryAgent(
        use_database=True,  # Use database instead of files
        llm_client=None     # No LLM for this example
    )
    
    print("✓ MemoryAgent initialized with database storage")
    
    # List available tools
    tools = agent.get_available_tools()
    print(f"✓ Available tools: {len(tools)} tools")
    
    for tool in tools:
        tool_name = tool['function']['name']
        tool_desc = tool['function']['description']
        print(f"   - {tool_name}: {tool_desc}")
    
    # Test some tools
    print(f"\n🔧 Testing MemoryAgent tools:")
    
    # List characters
    result = agent.list_available_characters()
    if result['success']:
        characters = result['characters']
        print(f"✓ Found {len(characters)} characters: {', '.join(characters)}")
    else:
        print(f"✗ Failed to list characters: {result.get('error')}")
        return
    
    # Get character info
    if characters:
        test_char = characters[0]
        result = agent.get_character_info(test_char)
        if result['success']:
            print(f"✓ Character info for {test_char}:")
            print(f"   - Exists: {result.get('exists', False)}")
            content = result.get('content', {})
            for content_type, info in content.items():
                print(f"   - {content_type}: {info.get('length', 0)} chars")
        else:
            print(f"✗ Failed to get info for {test_char}")
    
    # Test vector search tool if available
    tools_list = [tool['function']['name'] for tool in tools]
    if 'search_similar_content' in tools_list:
        print(f"\n🔍 Testing vector search tool:")
        result = agent.search_similar_content(
            query="programming skills and technical expertise",
            limit=2
        )
        if result['success']:
            print(f"✓ Found {result['total_found']} similar items")
            for item in result['results'][:2]:
                print(f"   - {item['character_name']}: {item['similarity_score']:.3f} similarity")
        else:
            print(f"✗ Vector search failed: {result.get('error')}")

def example_file_vs_database_comparison():
    """Example comparing file storage vs database storage"""
    print("\n=== File vs Database Storage Comparison ===")
    
    # File-based agent
    file_agent = MemoryAgent(
        use_database=False,  # Use file storage
        memory_dir="example_memory"
    )
    print("✓ File-based MemoryAgent created")
    
    # Database-based agent  
    db_agent = MemoryAgent(
        use_database=True   # Use database storage
    )
    print("✓ Database-based MemoryAgent created")
    
    # Compare available tools
    file_tools = [tool['function']['name'] for tool in file_agent.get_available_tools()]
    db_tools = [tool['function']['name'] for tool in db_agent.get_available_tools()]
    
    print(f"\n📊 Tool Comparison:")
    print(f"   File storage tools: {len(file_tools)}")
    print(f"   Database storage tools: {len(db_tools)}")
    
    # Tools only available in database mode
    db_only_tools = set(db_tools) - set(file_tools)
    if db_only_tools:
        print(f"   Database-only tools: {', '.join(db_only_tools)}")
    
    print(f"\n🏗️ Architecture Comparison:")
    print(f"   File mode: Agent → File Manager → .md files")
    print(f"   Database mode: Agent → Database Manager → PostgreSQL + pgvector")
    
    print(f"\n✨ Database Benefits:")
    print(f"   • Automatic embedding generation")
    print(f"   • Vector similarity search") 
    print(f"   • Structured storage with metadata")
    print(f"   • Better performance for large datasets")
    print(f"   • Concurrent access support")

def example_custom_embedding_client():
    """Example of using custom embedding client"""
    print("\n=== Custom Embedding Client Example ===")
    
    # Example: Create a mock embedding client
    class MockEmbeddingClient:
        def embed(self, text):
            # Return a simple mock embedding (normally would use a real model)
            return [0.1] * 1536  # OpenAI embedding dimension
        
        def get_embedding_dimension(self):
            return 1536
    
    # Create database manager with custom embedding
    db_manager = MemoryDatabaseManager()
    mock_client = MockEmbeddingClient()
    db_manager.set_embedding_client(mock_client)
    
    print("✓ Custom embedding client configured")
    print("💡 In practice, you could use:")
    print("   • Sentence Transformers")
    print("   • Hugging Face models")
    print("   • Azure OpenAI") 
    print("   • Custom embedding services")

def main():
    """Run all database storage examples"""
    print("MemU Database Storage Examples")
    print("=" * 50)
    
    try:
        # Basic database storage
        example_database_storage()
        
        # Vector search capabilities
        example_vector_search()
        
        # MemoryAgent with database
        example_memory_agent_database()
        
        # Storage comparison
        example_file_vs_database_comparison()
        
        # Custom embedding
        example_custom_embedding_client()
        
        print("\n" + "=" * 50)
        print("✅ All database examples completed!")
        
        print("\n💡 Key Takeaways:")
        print("• Database storage provides structured, scalable memory management")
        print("• Automatic embedding generation enables semantic search")
        print("• MemoryAgent seamlessly supports both file and database backends")
        print("• Vector search unlocks powerful similarity-based memory retrieval")
        print("• Hybrid approach allows choosing the best storage for your use case")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 