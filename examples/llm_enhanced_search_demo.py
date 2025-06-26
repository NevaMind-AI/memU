"""
PersonaLab LLM-Enhanced Search Demo

This demo showcases the LLM-enhanced search functionality including:
- llm_need_search function for intelligent search decision making using LLM
- llm_deep_search function with LLM-powered relevance judgment
- Comparison between rule-based and LLM-based search decisions
- Fallback behavior when LLM is not available
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab.main import Memory

# Try to import LLM for enhanced functionality
try:
    from personalab.llm import LLMManager
    LLM_AVAILABLE = True
    print("LLM module available - enhanced features enabled")
except ImportError:
    LLMManager = None
    LLM_AVAILABLE = False
    print("LLM module not available - using fallback mode")


def setup_demo_memory_with_llm():
    """Set up a memory instance with LLM support for demonstration."""
    # Try to create memory with LLM support
    llm_instance = None
    
    if LLM_AVAILABLE:
        try:
            llm_manager = LLMManager.create_quick_setup()
            llm_instance = llm_manager.get_current_provider()
            if llm_instance:
                print(f"Using LLM: {type(llm_instance).__name__}")
            else:
                print("No LLM providers available")
        except Exception as e:
            print(f"Could not initialize LLM: {e}")
            llm_instance = None
    
    # Create memory with LLM enhancement
    memory = Memory(
        "llm_enhanced_agent", 
        enable_deep_search=True,
        llm_instance=llm_instance,
        enable_llm_judgment=True
    )
    
    # Set up comprehensive test data
    agent_profile = """
    I am an advanced AI assistant with expertise in multiple domains:
    - Machine Learning and Deep Learning (TensorFlow, PyTorch, scikit-learn)
    - Data Science and Analytics (pandas, numpy, matplotlib, seaborn)
    - Software Development (Python, JavaScript, React, Node.js)
    - Cloud Computing (AWS, Google Cloud, Azure)
    - Natural Language Processing and Computer Vision
    - Project Management and Technical Consulting
    
    I specialize in helping users with complex technical projects,
    data analysis, model development, and system architecture.
    """
    
    memory.agent_memory.profile.set_profile(agent_profile.strip())
    
    # Add diverse agent events
    agent_events = [
        "Helped user implement a customer churn prediction model using XGBoost",
        "Designed and deployed a real-time recommendation system on AWS",
        "Created automated data pipeline using Apache Airflow and Docker",
        "Optimized neural network architecture for image classification task",
        "Developed React dashboard for business intelligence and analytics",
        "Implemented NLP sentiment analysis for social media monitoring",
        "Architected microservices infrastructure using Kubernetes",
        "Built machine learning model monitoring and alerting system",
        "Created data visualization suite using D3.js and Python Dash",
        "Developed automated testing framework for ML model validation"
    ]
    
    for event in agent_events:
        memory.agent_memory.events.add_memory(event)
    
    # Set up user memory with detailed context
    user_memory = memory.get_user_memory("data_scientist_alice")
    
    user_profile = """
    Senior Data Scientist at TechFlow Analytics with 5 years experience.
    Currently leading the customer analytics and retention team.
    
    Technical Expertise:
    - Advanced Statistics and Machine Learning
    - Python, R, SQL, and Spark
    - Cloud platforms (AWS, GCP)
    - Model deployment and MLOps
    
    Current Projects:
    - Customer lifetime value prediction model
    - Real-time fraud detection system
    - A/B testing platform development
    - Marketing attribution analysis
    
    Interests: Deep learning, NLP, recommendation systems, and business intelligence.
    """
    
    user_memory.profile.set_profile(user_profile.strip())
    
    # Add detailed user events
    user_events = [
        "Started customer lifetime value (CLV) prediction project using historical transaction data",
        "Implemented feature engineering pipeline for behavioral analytics",
        "Experimented with ensemble methods: Random Forest, XGBoost, and LightGBM",
        "Built real-time model serving infrastructure using FastAPI and Redis",
        "Conducted A/B test analysis for new recommendation algorithm",
        "Presented quarterly business impact report to executive team",
        "Collaborated on fraud detection system using anomaly detection techniques",
        "Developed automated model retraining pipeline with data drift monitoring",
        "Integrated attribution modeling with marketing spend optimization",
        "Researched advanced deep learning approaches for sequential data"
    ]
    
    for event in user_events:
        user_memory.events.add_memory(event)
    
    return memory


def demo_llm_need_search():
    """Demonstrate LLM-enhanced search decision making."""
    print("=== LLM-ENHANCED NEED SEARCH DEMO ===\n")
    
    memory = setup_demo_memory_with_llm()
    
    # Test various conversation scenarios
    test_scenarios = [
        {
            "conversation": "What's the current weather forecast?",
            "description": "General query unrelated to memory (should NOT trigger search)"
        },
        {
            "conversation": "Can you remind me about the CLV project I mentioned last week?",
            "description": "Direct memory reference with temporal context (should trigger search)"
        },
        {
            "conversation": "How should I approach ensemble modeling for my current project?",
            "description": "Technical question that benefits from personal context (might trigger search)"
        },
        {
            "conversation": "Let's continue working on the fraud detection system we discussed.",
            "description": "Continuation of previous topic (should trigger search)"
        },
        {
            "conversation": "What's the best practice for model deployment?",
            "description": "General technical question (might not need search)"
        },
        {
            "conversation": "How is my A/B testing project progressing based on our last discussion?",
            "description": "Status inquiry requiring memory context (should trigger search)"
        },
        {
            "conversation": "I need help with the attribution modeling approach we talked about.",
            "description": "Reference to previous conversation (should trigger search)"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        conversation = scenario["conversation"]
        description = scenario["description"]
        
        print(f"{i}. {description}")
        print(f"   Query: \"{conversation}\"")
        
        # Compare different search decision methods
        basic_need = memory.should_search_memory(conversation)
        enhanced_need = memory.need_search(conversation, context_length=800)
        llm_need = memory.llm_need_search(conversation, context_length=800)
        
        print(f"   Basic search needed: {basic_need}")
        print(f"   Enhanced search needed: {enhanced_need}")
        print(f"   LLM search needed: {llm_need}")
        
        # Show if there are differences in decisions
        if basic_need != llm_need or enhanced_need != llm_need:
            print(f"   📝 Note: Different methods gave different results!")
        
        print()


def demo_llm_deep_search():
    """Demonstrate LLM-enhanced deep search functionality."""
    print("=== LLM-ENHANCED DEEP SEARCH DEMO ===\n")
    
    memory = setup_demo_memory_with_llm()
    
    # Test complex search scenarios
    search_scenarios = [
        {
            "conversation": "What machine learning approaches have we explored for my customer analytics project?",
            "user_id": "data_scientist_alice",
            "description": "Complex query about specific project approaches"
        },
        {
            "conversation": "Show me the progress on real-time systems we've discussed.",
            "user_id": "data_scientist_alice", 
            "description": "Broad query about system development topics"
        },
        {
            "conversation": "What were the key insights from my fraud detection research?",
            "user_id": "data_scientist_alice",
            "description": "Research-focused query requiring detailed context"
        },
        {
            "conversation": "Help me understand the deployment and MLOps work we've covered.",
            "user_id": "data_scientist_alice",
            "description": "Technical infrastructure and operations query"
        }
    ]
    
    for i, scenario in enumerate(search_scenarios, 1):
        conversation = scenario["conversation"]
        user_id = scenario.get("user_id")
        description = scenario["description"]
        
        print(f"{i}. {description}")
        print(f"   Query: \"{conversation}\"")
        print()
        
        # Perform LLM-enhanced deep search
        results = memory.llm_deep_search(
            conversation=conversation,
            user_id=user_id,
            max_results=8,
            similarity_threshold=50.0
        )
        
        print(f"   Results found: {results['results_found']}")
        print(f"   Search terms: {results['search_terms'][:5]}...")  # Show first 5 terms
        
        # Display LLM enhancement metadata
        metadata = results['deep_search_metadata']
        print(f"   LLM enhanced: {metadata.get('llm_enhanced', False)}")
        print(f"   LLM ranking applied: {metadata.get('llm_ranking_applied', False)}")
        
        if results['relevant_context']:
            print(f"   Enhanced context preview:")
            context_preview = results['relevant_context'][:400]
            print(f"   {context_preview}{'...' if len(results['relevant_context']) > 400 else ''}")
        
        print("\n" + "="*80 + "\n")


def demo_search_comparison():
    """Compare different search methods: basic, enhanced, and LLM-enhanced."""
    print("=== SEARCH METHOD COMPARISON ===\n")
    
    memory = setup_demo_memory_with_llm()
    
    query = "What advanced techniques and infrastructure have we implemented for my data science projects?"
    user_id = "data_scientist_alice"
    
    print(f"Query: \"{query}\"")
    print(f"User: {user_id}")
    print()
    
    # Basic search
    print("1. BASIC SEARCH:")
    basic_results = memory.search_memory_with_context(
        conversation=query,
        user_id=user_id,
        max_results=5
    )
    
    print(f"   Results: {basic_results['results_found']}")
    print(f"   Terms: {basic_results['search_terms'][:3]}...")
    
    # Enhanced search
    print("\n2. ENHANCED DEEP SEARCH:")
    enhanced_results = memory.deep_search(
        conversation=query,
        user_id=user_id,
        max_results=5,
        similarity_threshold=50.0
    )
    
    print(f"   Results: {enhanced_results['results_found']}")
    print(f"   Terms: {enhanced_results['search_terms'][:3]}...")
    print(f"   Cross-refs: {enhanced_results['deep_search_metadata']['cross_references']}")
    
    # LLM-enhanced search
    print("\n3. LLM-ENHANCED SEARCH:")
    llm_results = memory.llm_deep_search(
        conversation=query,
        user_id=user_id,
        max_results=5,
        similarity_threshold=50.0
    )
    
    print(f"   Results: {llm_results['results_found']}")
    print(f"   Terms: {llm_results['search_terms'][:3]}...")
    
    llm_metadata = llm_results['deep_search_metadata']
    print(f"   LLM enhanced: {llm_metadata.get('llm_enhanced', False)}")
    print(f"   LLM ranking: {llm_metadata.get('llm_ranking_applied', False)}")
    
    # Show quality differences
    print("\n4. RESULT QUALITY COMPARISON:")
    print(f"   Basic context length: {len(basic_results.get('relevant_context', ''))}")
    print(f"   Enhanced context length: {len(enhanced_results.get('relevant_context', ''))}")
    print(f"   LLM-enhanced context length: {len(llm_results.get('relevant_context', ''))}")


def demo_fallback_behavior():
    """Demonstrate fallback behavior when LLM is not available."""
    print("=== FALLBACK BEHAVIOR DEMO ===\n")
    
    # Create memory without LLM
    memory_no_llm = Memory(
        "fallback_agent", 
        enable_deep_search=True,
        llm_instance=None,
        enable_llm_judgment=False
    )
    
    # Add minimal test data
    memory_no_llm.agent_memory.profile.set_profile("I am a basic AI assistant.")
    memory_no_llm.agent_memory.events.add_memory("Had a conversation about data analysis.")
    
    query = "Tell me about our previous data analysis discussion."
    
    print(f"Query: \"{query}\"")
    print(f"LLM judgment enabled: {memory_no_llm.enable_llm_judgment}")
    print(f"LLM instance available: {memory_no_llm.llm is not None}")
    print()
    
    # Test LLM methods (should fallback)
    print("Testing LLM methods with fallback:")
    
    llm_need = memory_no_llm.llm_need_search(query)
    print(f"   llm_need_search result: {llm_need} (fallback to enhanced)")
    
    llm_search_results = memory_no_llm.llm_deep_search(query)
    print(f"   llm_deep_search results: {llm_search_results['results_found']} (fallback to regular)")
    print(f"   Has LLM metadata: {'llm_enhanced' in llm_search_results.get('deep_search_metadata', {})}")


def demo_error_handling():
    """Demonstrate error handling in LLM-enhanced search."""
    print("=== ERROR HANDLING DEMO ===\n")
    
    # Create memory with LLM support
    memory = setup_demo_memory_with_llm()
    
    # Test with edge cases
    edge_cases = [
        "",  # Empty query
        "a",  # Very short query
        "?" * 100,  # Very long query with special characters
        "Normal query about machine learning projects"  # Normal case
    ]
    
    for i, query in enumerate(edge_cases, 1):
        query_display = query[:50] + "..." if len(query) > 50 else query
        query_display = query_display or "[empty string]"
        
        print(f"{i}. Testing with: \"{query_display}\"")
        
        try:
            # Test LLM need search
            need_result = memory.llm_need_search(query)
            print(f"   llm_need_search: {need_result} ✓")
            
            # Test LLM deep search
            search_result = memory.llm_deep_search(query, max_results=3)
            print(f"   llm_deep_search: {search_result['results_found']} results ✓")
            
        except Exception as e:
            print(f"   Error: {e} ❌")
        
        print()


if __name__ == "__main__":
    print("PersonaLab LLM-Enhanced Search Functionality Demo")
    print("=" * 60)
    print()
    
    try:
        # Run all demos
        demo_llm_need_search()
        print()
        
        demo_llm_deep_search()
        print()
        
        demo_search_comparison()
        print()
        
        demo_fallback_behavior()
        print()
        
        demo_error_handling()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc() 