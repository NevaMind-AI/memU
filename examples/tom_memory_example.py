#!/usr/bin/env python3
"""
Theory of Mind Memory Example for PersonaLab

This example demonstrates the Theory of Mind (ToM) capabilities of PersonaLab,
showing how the system can analyze psychological patterns, motivations, and
behavioral insights from conversations.

Features demonstrated:
- ToM memory component usage
- Psychological insight generation
- Behavior pattern analysis
- Confidence scoring for insights
- Memory integration with ToM data

Run this example to see how PersonaLab can build psychological profiles
and understand user motivations through conversation analysis.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from personalab.memory.base import Memory, ToMMemory
from personalab.memory import MemoryManager
from personalab.llm import LLMManager


def basic_tom_memory_example():
    """Demonstrates basic Theory of Mind memory operations."""
    print("=== Basic ToM Memory Example ===\n")
    
    # Create a ToM memory component
    tom_memory = ToMMemory()
    
    # Add psychological insights
    insights = [
        "User demonstrates strong motivation for technical learning",
        "User prefers hands-on learning approaches over theoretical study",
        "User shows problem-solving persistence when facing challenges",
        "User exhibits introversion but becomes expressive about technical topics"
    ]
    
    for insight in insights:
        tom_memory.add_insight(insight)
    
    print("Added psychological insights:")
    for i, insight in enumerate(tom_memory.get_content(), 1):
        print(f"{i}. {insight}")
    
    print(f"\nTotal insights: {tom_memory.get_insight_count()}")
    
    # Search for specific insights
    tech_insights = tom_memory.search_insights("technical")
    print(f"\nTechnical-related insights: {len(tech_insights)}")
    for insight in tech_insights:
        print(f"- {insight}")
    
    learning_insights = tom_memory.search_insights("learning")
    print(f"\nLearning-related insights: {len(learning_insights)}")
    for insight in learning_insights:
        print(f"- {insight}")
    
    return tom_memory


def unified_memory_with_tom_example():
    """Demonstrates unified Memory class with ToM integration."""
    print("\n=== Unified Memory with ToM Example ===\n")
    
    # Create unified memory instance
    memory = Memory(agent_id="ai_researcher_001")
    
    # Set up profile
    memory.update_profile("User is an AI researcher with strong technical background")
    memory.update_events([
        "User inquired about transformer architecture principles", 
        "User implemented attention mechanism from scratch"
    ])
    
    # Add ToM insights
    psychological_insights = [
        "User demonstrates deep technical curiosity",
        "User has strong analytical thinking patterns",
        "User prefers understanding fundamentals before implementation",
        "User shows collaborative learning tendencies"
    ]
    
    memory.update_tom(psychological_insights)
    
    # Display complete memory content
    print("Complete Memory Profile:")
    print(memory.to_prompt())
    
    # Get memory summary
    summary = memory.get_memory_summary()
    print("Memory Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    return memory


def llm_enhanced_tom_example():
    """Demonstrates LLM-enhanced ToM analysis using the pipeline."""
    print("\n=== LLM-Enhanced ToM Analysis Example ===\n")
    
    try:
        # Initialize LLM manager
        llm_manager = LLMManager.create_quick_setup()
        
        # Create memory manager with LLM
        memory_manager = MemoryManager(
            db_path="tom_example_memory.db",
            llm_client=llm_manager.get_current_provider()
        )
        
        # Get or create memory for an agent
        agent_id = "learning_assistant"
        memory = memory_manager.get_or_create_memory(agent_id)
        
        # Simulate a conversation that reveals psychological patterns
        conversation = [
            {
                "role": "user", 
                "content": "I'm struggling with machine learning concepts. I prefer to understand the math behind algorithms before using libraries."
            },
            {
                "role": "assistant", 
                "content": "That's a great approach! Understanding the fundamentals helps build intuition. Would you like to start with linear regression mathematics?"
            },
            {
                "role": "user", 
                "content": "Yes, please. I learn best when I can derive the equations myself and then see practical examples."
            },
            {
                "role": "assistant", 
                "content": "Perfect! Let's derive the least squares solution step by step, then implement it from scratch before using scikit-learn."
            }
        ]
        
        # Update memory with conversation (this will trigger ToM analysis)
        updated_memory, pipeline_result = memory_manager.update_memory_with_conversation(
            agent_id, 
            conversation
        )
        
        print("Analysis Results:")
        print("Profile:", updated_memory.get_profile_content())
        print("\nEvents:", updated_memory.get_event_content())
        print("\nToM Insights:", updated_memory.get_tom_content())
        
        # Display pipeline results
        if pipeline_result:
            print("\nPipeline Execution Results:")
            print(f"Profile Updated: {pipeline_result.update_result.profile_updated}")
            
            if hasattr(pipeline_result, 'tom_result'):
                print(f"ToM Confidence: {pipeline_result.tom_result.confidence_score}")
                print(f"ToM Insights: {pipeline_result.tom_result.insights}")
        
    except Exception as e:
        print(f"LLM-enhanced example requires LLM configuration: {e}")
        print("Please set up your LLM API keys to see ToM analysis in action.")
        
        # Fallback to manual ToM insights
        print("\nFallback: Manual ToM Analysis")
        memory = Memory(agent_id="learning_assistant")
        memory.update_profile("User prefers understanding fundamentals before practical application")
        memory.update_events(["User asked about ML math", "User wants to derive equations"])
        
        manual_insights = [
            "User demonstrates analytical learning style",
            "User values deep understanding over quick implementation",
            "User shows mathematical thinking preference",
            "User likely has strong theoretical background"
        ]
        memory.update_tom(manual_insights)
        
        print("\nManual ToM Analysis:")
        print(memory.to_prompt())


def tom_confidence_and_metadata_example():
    """Demonstrates ToM confidence scoring and metadata handling."""
    print("\n=== ToM Confidence and Metadata Example ===\n")
    
    memory = Memory(agent_id="personality_analysis_subject")
    
    # Add insights with confidence indicators
    insights_with_context = [
        "User shows strong preference for systematic approaches (confidence: high)",
        "User may have perfectionist tendencies (confidence: medium)", 
        "User demonstrates patience in learning process (confidence: high)",
        "User possibly has introverted personality traits (confidence: low)"
    ]
    
    memory.update_tom(insights_with_context)
    
    # Simulate confidence metadata
    tom_metadata = {
        "insights": "\n".join(insights_with_context),
        "confidence_score": 0.75,
        "analysis_timestamp": "2024-01-15T10:30:00Z",
        "insight_count": len(insights_with_context),
        "high_confidence_count": 2,
        "medium_confidence_count": 1,
        "low_confidence_count": 1
    }
    
    # Set metadata (using backward compatibility)
    memory.tom_metadata = tom_metadata
    
    print("ToM Analysis with Confidence Scoring:")
    print(f"Overall Confidence Score: {tom_metadata['confidence_score']}")
    print(f"High Confidence Insights: {tom_metadata['high_confidence_count']}")
    print(f"Medium Confidence Insights: {tom_metadata['medium_confidence_count']}")
    print(f"Low Confidence Insights: {tom_metadata['low_confidence_count']}")
    
    print("\nDetailed Insights:")
    for insight in memory.get_tom_content():
        print(f"- {insight}")
    
    # Demonstrate metadata retrieval
    retrieved_metadata = memory.tom_metadata
    if retrieved_metadata:
        print(f"\nRetrieved Confidence Score: {retrieved_metadata.get('confidence_score', 'N/A')}")


def main():
    """Run all ToM memory examples."""
    print("PersonaLab Theory of Mind Memory Examples")
    print("=" * 50)
    
    try:
        # Run basic ToM memory example
        tom_memory = basic_tom_memory_example()
        
        # Run unified memory with ToM example
        unified_memory = unified_memory_with_tom_example()
        
        # Run LLM-enhanced ToM example
        llm_enhanced_tom_example()
        
        # Run confidence and metadata example
        tom_confidence_and_metadata_example()
        
        print("\n" + "=" * 50)
        print("All ToM examples completed successfully!")
        print("\nKey takeaways:")
        print("1. ToM memory stores psychological insights about users")
        print("2. Insights can be searched and filtered by keywords")
        print("3. LLM integration enables automatic psychological analysis")
        print("4. Confidence scoring helps assess insight reliability")
        print("5. ToM integrates seamlessly with profile and event memory")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 