"""
PersonaLab Deep Search Demo

This demo showcases the enhanced deep search functionality including:
- need_search function for intelligent search decision making
- deep_search function with advanced relevance scoring
- Cross-reference analysis between agent and user memories
- Enhanced context extraction and formatting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab.main import Memory


def setup_demo_memory():
    """Set up a memory instance with sample data for demonstration."""
    # Create memory with deep search enabled
    memory = Memory("demo_agent", enable_deep_search=True)
    
    # Set up agent memory
    agent_profile = """
    I am an AI assistant specialized in data science and machine learning.
    I have expertise in Python, R, and statistical analysis.
    I enjoy helping users with data visualization and predictive modeling.
    My background includes working with pandas, scikit-learn, and TensorFlow.
    I have experience with both supervised and unsupervised learning techniques.
    """
    
    memory.agent_memory.profile.set_profile(agent_profile.strip())
    
    # Add agent events
    agent_events = [
        "Helped user analyze customer churn data using logistic regression",
        "Created data visualization dashboard with matplotlib and seaborn",
        "Implemented neural network for image classification project",
        "Optimized random forest model for sales prediction",
        "Discussed feature engineering techniques for time series data"
    ]
    
    for event in agent_events:
        memory.agent_memory.events.add_memory(event)
    
    # Set up user memory
    user_memory = memory.get_user_memory("user123")
    
    user_profile = """
    Data scientist at TechCorp with 3 years of experience.
    Specializes in machine learning and predictive analytics.
    Currently working on customer segmentation project.
    Prefers Python and Jupyter notebooks for analysis.
    Interested in deep learning and natural language processing.
    """
    
    user_memory.profile.set_profile(user_profile.strip())
    
    # Add user events
    user_events = [
        "Started working on customer segmentation using k-means clustering",
        "Implemented data preprocessing pipeline with pandas",
        "Experimented with different feature scaling techniques",
        "Presented initial findings to the management team",
        "Requested help with model evaluation metrics"
    ]
    
    for event in user_events:
        user_memory.events.add_memory(event)
    
    return memory


def demo_need_search():
    """Demonstrate the need_search function."""
    print("=== NEED_SEARCH FUNCTION DEMO ===\n")
    
    memory = setup_demo_memory()
    
    # Test different conversation scenarios
    test_cases = [
        {
            "conversation": "What's the weather like today?",
            "description": "Simple weather query (should NOT trigger search)"
        },
        {
            "conversation": "Can you remember what machine learning project I'm working on?",
            "description": "Direct memory request (should trigger search)"
        },
        {
            "conversation": "How do I implement k-means clustering?",
            "description": "Technical question (might trigger search based on context)"
        },
        {
            "conversation": "Can you continue where we left off with the customer segmentation?",
            "description": "Continuation request (should trigger search)"
        },
        {
            "conversation": "My project needs better evaluation metrics. What did we discuss before?",
            "description": "Context-dependent query (should trigger search)"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        conversation = test_case["conversation"]
        description = test_case["description"]
        
        # Test with different context lengths
        basic_need = memory.need_search(conversation)
        context_need = memory.need_search(conversation, context_length=1000)
        
        print(f"{i}. {description}")
        print(f"   Query: \"{conversation}\"")
        print(f"   Basic search needed: {basic_need}")
        print(f"   With context search needed: {context_need}")
        print()


def demo_deep_search():
    """Demonstrate the deep_search function."""
    print("=== DEEP_SEARCH FUNCTION DEMO ===\n")
    
    memory = setup_demo_memory()
    
    # Test different search scenarios
    search_scenarios = [
        {
            "conversation": "What machine learning techniques have we discussed for my customer project?",
            "user_id": "user123",
            "description": "Complex query involving both agent and user memory"
        },
        {
            "conversation": "Tell me about data visualization and analysis methods",
            "user_id": "user123",
            "description": "Broad technical query"
        },
        {
            "conversation": "What's my current project status and what help did I request?",
            "user_id": "user123",
            "description": "Personal context query"
        }
    ]
    
    for i, scenario in enumerate(search_scenarios, 1):
        conversation = scenario["conversation"]
        user_id = scenario.get("user_id")
        description = scenario["description"]
        
        print(f"{i}. {description}")
        print(f"   Query: \"{conversation}\"")
        print()
        
        # Perform deep search
        results = memory.deep_search(
            conversation=conversation,
            user_id=user_id,
            max_results=10,
            similarity_threshold=50.0
        )
        
        print(f"   Results found: {results['results_found']}")
        print(f"   Search terms: {results['search_terms']}")
        
        # Display metadata
        metadata = results['deep_search_metadata']
        print(f"   Metadata:")
        print(f"     - Total results before filter: {metadata['total_results_before_filter']}")
        print(f"     - Cross-references found: {metadata['cross_references']}")
        print(f"     - Search categories: {metadata['search_categories']}")
        print(f"     - Source distribution: {metadata['source_distribution']}")
        
        if results['relevant_context']:
            print(f"   Relevant context:")
            print(f"   {results['relevant_context'][:500]}{'...' if len(results['relevant_context']) > 500 else ''}")
        
        print("\n" + "="*80 + "\n")


def demo_comparison():
    """Compare basic search vs deep search."""
    print("=== BASIC vs DEEP SEARCH COMPARISON ===\n")
    
    memory = setup_demo_memory()
    
    query = "What machine learning projects and techniques have we worked on together?"
    user_id = "user123"
    
    print(f"Query: \"{query}\"")
    print()
    
    # Basic search
    print("BASIC SEARCH RESULTS:")
    basic_results = memory.search_memory_with_context(
        conversation=query,
        user_id=user_id,
        max_results=10
    )
    
    print(f"Results found: {basic_results['results_found']}")
    print(f"Search terms: {basic_results['search_terms']}")
    if basic_results['relevant_context']:
        print(f"Context: {basic_results['relevant_context'][:300]}...")
    
    print("\n" + "-"*60 + "\n")
    
    # Deep search
    print("DEEP SEARCH RESULTS:")
    deep_results = memory.deep_search(
        conversation=query,
        user_id=user_id,
        max_results=10,
        similarity_threshold=40.0
    )
    
    print(f"Results found: {deep_results['results_found']}")
    print(f"Enhanced search terms: {deep_results['search_terms']}")
    
    metadata = deep_results['deep_search_metadata']
    print(f"Enhanced features:")
    print(f"  - Cross-references: {metadata['cross_references']}")
    print(f"  - Relevance scores: {[f'{score:.1f}' for score in metadata['relevance_scores'][:3]]}")
    print(f"  - Categories: {metadata['search_categories']}")
    
    if deep_results['relevant_context']:
        print(f"Enhanced context: {deep_results['relevant_context'][:400]}...")


def demo_deep_search_disabled():
    """Demonstrate behavior when deep search is disabled."""
    print("=== DEEP SEARCH DISABLED DEMO ===\n")
    
    # Create memory with deep search disabled
    memory = Memory("demo_agent", enable_deep_search=False)
    
    # Set up minimal data
    memory.agent_memory.profile.set_profile("I am a basic AI assistant.")
    memory.agent_memory.events.add_memory("Had a conversation about weather.")
    
    query = "What did we discuss before about weather patterns?"
    
    print(f"Query: \"{query}\"")
    print(f"Deep search enabled: {memory.enable_deep_search}")
    print()
    
    # Test need_search (should fall back to basic)
    need = memory.need_search(query)
    print(f"Need search result: {need}")
    
    # Test deep_search (should fall back to basic search)
    results = memory.deep_search(query)
    print(f"Deep search results (fallback): {results['results_found']} results")
    print(f"Has deep search metadata: {'deep_search_metadata' in results}")


if __name__ == "__main__":
    print("PersonaLab Deep Search Functionality Demo")
    print("=" * 50)
    print()
    
    try:
        # Run all demos
        demo_need_search()
        print()
        
        demo_deep_search()
        print()
        
        demo_comparison()
        print()
        
        demo_deep_search_disabled()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc() 