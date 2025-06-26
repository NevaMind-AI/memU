"""
PersonaLab LLM-Only Search Demo

This demo showcases the fully LLM-based search functionality where:
- All search decisions are made by LLM analysis
- All content matching and relevance scoring is done by LLM
- No keyword matching or rule-based patterns are used
- Falls back gracefully when LLM is unavailable
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalab.main import Memory

# Try to import LLM for functionality
try:
    from personalab.llm import LLMManager
    LLM_AVAILABLE = True
    print("LLM module available - LLM-only search enabled")
except ImportError:
    LLMManager = None
    LLM_AVAILABLE = False
    print("LLM module not available - will use fallback methods")


def setup_comprehensive_memory():
    """Set up a memory instance with rich content for LLM analysis."""
    # Create memory with LLM support
    memory = Memory("llm_only_agent", enable_deep_search=True, enable_llm_judgment=True)
    
    # Set up detailed agent memory
    agent_profile = """
    I am an advanced AI research assistant with deep expertise in:
    
    Technical Domains:
    - Machine Learning & Deep Learning (PyTorch, TensorFlow, Transformers)
    - Natural Language Processing (BERT, GPT, T5, tokenization, embeddings)
    - Computer Vision (CNNs, object detection, image segmentation, GANs)
    - Reinforcement Learning (Q-learning, policy gradients, DDPG, PPO)
    - MLOps & Production Systems (Docker, Kubernetes, model serving, monitoring)
    
    Research Areas:
    - Foundation models and large language models
    - Multimodal AI and vision-language models
    - Meta-learning and few-shot learning
    - Explainable AI and model interpretability
    - Ethical AI and bias mitigation
    
    Programming & Tools:
    - Python ecosystem (pandas, numpy, scikit-learn, matplotlib)
    - Cloud platforms (AWS, GCP, Azure) 
    - Distributed computing (Ray, Dask, Spark)
    - Version control and collaboration (Git, MLflow, Weights & Biases)
    
    I specialize in helping researchers and engineers with:
    - Experimental design and hypothesis testing
    - Model architecture selection and optimization
    - Data preprocessing and feature engineering
    - Performance evaluation and benchmarking
    - Research paper analysis and implementation
    """
    
    memory.agent_memory.profile.set_profile(agent_profile.strip())
    
    # Add detailed agent events covering various topics
    agent_events = [
        "Helped implement a transformer-based sentiment analysis model using BERT, achieving 94% accuracy on customer review data",
        "Designed and deployed a real-time recommendation system using collaborative filtering and neural collaborative filtering, serving 10M+ users daily",
        "Optimized a computer vision pipeline for autonomous vehicle perception, reducing inference latency from 200ms to 50ms while maintaining 99.2% accuracy",
        "Implemented a multi-agent reinforcement learning system for resource allocation in cloud computing environments",
        "Developed an explainable AI framework for medical diagnosis, providing interpretable predictions for radiological image analysis"
    ]
    
    for event in agent_events:
        memory.agent_memory.events.add_memory(event)
    
    # Set up detailed user memory
    user_memory = memory.get_user_memory("ai_researcher_sarah")
    
    user_profile = """
    Dr. Sarah Chen - Senior AI Research Scientist at DeepTech Labs
    
    Background:
    - PhD in Computer Science from Stanford, specializing in Natural Language Processing
    - 8 years of experience in AI research and development
    - Published 25+ papers in top-tier conferences (NeurIPS, ICML, ACL, ICLR)
    - Expert in transformer architectures and large language models
    
    Current Research Focus:
    - Efficient training of large language models
    - Multi-modal learning and vision-language understanding
    - Reasoning capabilities in AI systems
    - Safe and aligned AI development
    
    Active Projects:
    1. "EfficientLLM" - Developing parameter-efficient fine-tuning methods for large language models
    2. "VisionReason" - Building AI systems that can reason about visual scenes and answer complex questions
    3. "SafeAI" - Researching methods for detecting and mitigating harmful outputs in AI systems
    4. "MetaLearn" - Exploring few-shot learning capabilities in foundation models
    """
    
    user_memory.profile.set_profile(user_profile.strip())
    
    # Add detailed user events showing research progress
    user_events = [
        "Started the EfficientLLM project focused on parameter-efficient fine-tuning techniques for large language models with limited computational resources",
        "Implemented LoRA (Low-Rank Adaptation) for fine-tuning BERT and GPT models, achieving 95% of full fine-tuning performance with only 0.1% trainable parameters",
        "Experimented with prefix tuning and prompt tuning methods, comparing their effectiveness across different downstream tasks and model sizes",
        "Conducted comprehensive experiments on adapter modules, testing various architectures and bottleneck dimensions for optimal efficiency",
        "Presented preliminary results at the Internal Research Symposium, receiving positive feedback on the practical impact for resource-constrained environments"
    ]
    
    for event in user_events:
        user_memory.events.add_memory(event)
    
    return memory


def demo_llm_search_decisions():
    """Demonstrate LLM-based search decision making."""
    print("=== LLM-ONLY SEARCH DECISIONS ===\n")
    
    memory = setup_comprehensive_memory()
    
    # Test various types of queries
    test_queries = [
        {
            "query": "What's the weather like today?",
            "expected": "NO search needed",
            "reason": "General factual query unrelated to memory"
        },
        {
            "query": "How is my EfficientLLM project progressing?",
            "expected": "NEEDS search",
            "reason": "Personal project status inquiry requiring memory context"
        },
        {
            "query": "Can you explain how transformer attention works?",
            "expected": "MAYBE search needed",
            "reason": "Technical question that might benefit from specific context"
        },
        {
            "query": "What were the results from my LoRA experiments?",
            "expected": "NEEDS search", 
            "reason": "Specific inquiry about past work and results"
        },
        {
            "query": "Continue our discussion about parameter-efficient fine-tuning",
            "expected": "NEEDS search",
            "reason": "Continuation request requiring previous context"
        }
    ]
    
    print(f"Memory status: {memory}")
    print(f"LLM available: {memory.llm is not None}")
    print(f"LLM judgment enabled: {memory.enable_llm_judgment}")
    print()
    
    for i, test in enumerate(test_queries, 1):
        query = test["query"]
        expected = test["expected"]
        reason = test["reason"]
        
        print(f"{i}. Query: \"{query}\"")
        print(f"   Expected: {expected}")
        print(f"   Reason: {reason}")
        
        # Use the new LLM-first search decision
        search_needed = memory.need_search(query, context_length=1000)
        
        print(f"   LLM Decision: {'SEARCH NEEDED' if search_needed else 'NO SEARCH'}")
        
        # Show whether this matches expectation
        if expected == "NEEDS search" and search_needed:
            print("   ✅ Correct decision")
        elif expected == "NO search needed" and not search_needed:
            print("   ✅ Correct decision")
        elif expected == "MAYBE search needed":
            print("   ℹ️ Reasonable decision (context-dependent)")
        else:
            print("   ⚠️ Unexpected decision")
        
        print()


def demo_llm_content_analysis():
    """Demonstrate LLM-based content analysis and relevance scoring."""
    print("=== LLM-ONLY CONTENT ANALYSIS ===\n")
    
    memory = setup_comprehensive_memory()
    
    # Test queries with different complexity levels
    analysis_queries = [
        {
            "query": "What methods have we explored for efficient training of large language models?",
            "focus": "Efficiency techniques and training methods",
            "user_id": "ai_researcher_sarah"
        },
        {
            "query": "Show me progress on multi-modal AI and vision-language research",
            "focus": "Multi-modal and vision-language work",
            "user_id": "ai_researcher_sarah"
        },
        {
            "query": "What collaboration opportunities have we discussed recently?",
            "focus": "Collaborative work and team interactions",
            "user_id": "ai_researcher_sarah"
        }
    ]
    
    for i, test in enumerate(analysis_queries, 1):
        query = test["query"]
        focus = test["focus"]
        user_id = test["user_id"]
        
        print(f"{i}. Analysis Query: \"{query}\"")
        print(f"   Focus Area: {focus}")
        print(f"   User Context: {user_id}")
        print()
        
        # Perform LLM-based deep search
        results = memory.deep_search(
            conversation=query,
            user_id=user_id,
            max_results=5,
            similarity_threshold=60.0
        )
        
        print(f"   Results Found: {results['results_found']}")
        
        # Show LLM analysis metadata
        metadata = results.get('deep_search_metadata', {})
        if metadata.get('llm_analyzed'):
            print(f"   ✅ LLM Analysis Applied")
            print(f"   Search Intent: {metadata.get('search_intent', 'N/A')}")
            
            relevance_scores = metadata.get('relevance_scores', [])
            if relevance_scores:
                print(f"   Relevance Scores: {[f'{score}' for score in relevance_scores]}")
            
            explanations = metadata.get('llm_explanations', [])
            if any(explanations):
                print("   LLM Explanations:")
                for j, explanation in enumerate(explanations[:3], 1):
                    if explanation:
                        print(f"     {j}. {explanation}")
        else:
            print(f"   ⚠️ Fallback to keyword-based search")
        
        # Show preview of found content
        if results['relevant_context']:
            preview = results['relevant_context'][:300]
            print(f"   Content Preview: {preview}...")
        
        print("\n" + "="*80 + "\n")


def demo_error_handling():
    """Demonstrate robust error handling in LLM-only search."""
    print("=== ERROR HANDLING & ROBUSTNESS ===\n")
    
    memory = setup_comprehensive_memory()
    
    # Test edge cases
    edge_cases = [
        ("", "Empty query"),
        ("?", "Single character"),
        ("What is 2+2?", "Simple math query"),
        ("Normal research question about our projects", "Normal case")
    ]
    
    print("Testing LLM-only search with various edge cases:")
    print()
    
    for i, (query, description) in enumerate(edge_cases, 1):
        query_display = query[:50] + "..." if len(query) > 50 else query
        query_display = query_display or "[empty]"
        
        print(f"{i}. {description}: \"{query_display}\"")
        
        try:
            # Test search decision
            need_search = memory.need_search(query)
            print(f"   Search Decision: {'NEEDED' if need_search else 'NOT NEEDED'} ✅")
            
            # Test search execution
            if need_search:
                results = memory.deep_search(query, max_results=2)
                print(f"   Search Results: {results['results_found']} items ✅")
                
                metadata = results.get('deep_search_metadata', {})
                if metadata.get('llm_analyzed'):
                    print(f"   LLM Analysis: SUCCESS ✅")
                elif metadata.get('llm_error'):
                    print(f"   LLM Analysis: FAILED, fallback used ⚠️")
                else:
                    print(f"   LLM Analysis: NOT APPLIED")
            else:
                print(f"   Search Not Performed (as expected)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()


if __name__ == "__main__":
    print("PersonaLab LLM-Only Search Functionality Demo")
    print("=" * 60)
    print()
    
    try:
        # Run all demos
        demo_llm_search_decisions()
        print()
        
        demo_llm_content_analysis()
        print()
        
        demo_error_handling()
        
        print("=" * 60)
        print("LLM-Only Search Demo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc() 