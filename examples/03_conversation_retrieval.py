#!/usr/bin/env python3
"""
PersonaLab Example 03: Conversation Retrieval
=============================================

This example demonstrates PersonaLab's conversation retrieval and search capabilities.

You'll learn how to:
- Record and store conversations automatically
- Search through conversation history
- Retrieve relevant past conversations
- Control retrieval behavior
- Understand conversation context building

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys:
   - OPENAI_API_KEY="your-openai-key"
   OR
   - ANTHROPIC_API_KEY="your-anthropic-key"
"""

import os
import time
from personalab import Persona


def demo_conversation_retrieval():
    """Demonstrate conversation retrieval and search capabilities"""
    print("🔍 PersonaLab Conversation Retrieval Demo")
    print("=" * 50)
    
    # Create persona with retrieval visibility
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')):
        print("❌ No API keys found! Using mock LLM for demonstration.")
        
        def mock_llm_function(messages, **kwargs):
            user_msg = messages[-1]['content'].lower()
            
            # Check if this is a context-enhanced message (contains retrieved conversations)
            full_content = messages[-1]['content']
            if "Previous conversations:" in full_content:
                return "I can see from our previous conversations that you've been working on some interesting projects. Let me use that context to give you a better response."
            
            # Regular responses
            if 'project' in user_msg:
                return f"That sounds like an interesting project! I'll remember this for future reference."
            elif 'remember' in user_msg or 'recall' in user_msg:
                return "Let me search through our previous conversations to find relevant information..."
            elif 'help' in user_msg or 'recommend' in user_msg:
                return "Based on what I know about you, I can provide some personalized recommendations."
            else:
                return f"Thank you for sharing that. I'm recording this conversation for future reference."
        
        from personalab.llm import CustomLLMClient
        custom_client = CustomLLMClient(llm_function=mock_llm_function)
        persona = Persona(
            agent_id="retrieval_demo_user",
            llm_client=custom_client,
            use_memory=True,
            use_memo=True,
            show_retrieval=True  # Show retrieval process
        )
        print("✅ Created persona with mock LLM and retrieval visibility\n")
    else:
        persona = Persona(
            agent_id="retrieval_demo_user",
            use_memory=True,
            use_memo=True,
            show_retrieval=True  # Show retrieval process
        )
        print("✅ Created persona with real LLM and retrieval visibility\n")
    
    # Step 1: Build conversation history
    print("Step 1: Building Conversation History")
    print("-" * 40)
    print("Let's have several conversations to build up a history...")
    
    # Day 1: Work project discussions
    print("\n📅 Day 1: Work Project Discussions")
    day1_conversations = [
        "I'm starting a new machine learning project at work.",
        "The project involves analyzing customer behavior data to predict churn.",
        "We're using Python, pandas, and scikit-learn for the initial prototype.",
        "The dataset has about 100,000 customer records with 50 features."
    ]
    
    for i, msg in enumerate(day1_conversations, 1):
        print(f"\n[Day 1 - Conversation {i}]")
        print(f"You: {msg}")
        try:
            response = persona.chat(msg)
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
        time.sleep(0.5)  # Brief pause for readability
    
    # Day 2: Technical challenges
    print("\n📅 Day 2: Technical Challenges")
    day2_conversations = [
        "I'm having trouble with feature engineering for the churn prediction model.",
        "The categorical variables have too many unique values, causing high dimensionality.",
        "I'm considering using target encoding or embeddings for categorical features.",
        "Also thinking about trying ensemble methods like Random Forest or XGBoost."
    ]
    
    for i, msg in enumerate(day2_conversations, 1):
        print(f"\n[Day 2 - Conversation {i}]")
        print(f"You: {msg}")
        try:
            response = persona.chat(msg)
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
        time.sleep(0.5)
    
    # Day 3: Personal interests
    print("\n📅 Day 3: Personal Interests")
    day3_conversations = [
        "Outside of work, I've been learning about deep learning frameworks.",
        "I'm particularly interested in computer vision and image classification.",
        "Been experimenting with PyTorch and TensorFlow for personal projects.",
        "Planning to build a photo classifier for my vacation pictures."
    ]
    
    for i, msg in enumerate(day3_conversations, 1):
        print(f"\n[Day 3 - Conversation {i}]")
        print(f"You: {msg}")
        try:
            response = persona.chat(msg)
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
        time.sleep(0.5)
    
    # Step 2: Manual search demonstrations
    print("\n" + "=" * 50)
    print("Step 2: Manual Search Demonstrations")
    print("-" * 40)
    
    search_queries = [
        "machine learning",
        "churn prediction", 
        "feature engineering",
        "deep learning",
        "computer vision",
        "Python"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")
        try:
            results = persona.search(query)
            if results:
                print(f"  Found {len(results)} relevant conversations:")
                for i, result in enumerate(results[:3], 1):  # Show top 3
                    summary = result.get('summary', 'No summary available')
                    print(f"    {i}. {summary[:100]}...")
            else:
                print("  No relevant conversations found.")
        except Exception as e:
            print(f"  Search error: {e}")
    
    # Step 3: Context-aware conversations
    print("\n" + "=" * 50)
    print("Step 3: Context-Aware Conversations")
    print("-" * 40)
    print("Now let's ask questions that should trigger automatic retrieval:")
    
    context_questions = [
        "What machine learning techniques have I mentioned before?",
        "Can you remind me about my work project details?",
        "What are my interests outside of work?", 
        "What programming tools and libraries have I used?",
        "Help me decide between Random Forest and XGBoost for my project."
    ]
    
    for i, question in enumerate(context_questions, 1):
        print(f"\n[Context Question {i}]")
        print(f"You: {question}")
        
        try:
            # This should automatically retrieve relevant conversations
            response = persona.chat(question, learn=False)  # Don't learn from meta questions
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
        
        print()  # Extra line for readability
    
    # Step 4: Retrieval behavior analysis
    print("\n" + "=" * 50)
    print("Step 4: Retrieval Behavior Analysis")
    print("-" * 40)
    
    # Turn off retrieval visibility to compare
    persona.show_retrieval = False
    print("🔇 Turned off retrieval visibility")
    
    print("\n💬 Same question without showing retrieval process:")
    try:
        response = persona.chat("What have I told you about my machine learning projects?", learn=False)
        print(f"AI: {response}")
    except Exception as e:
        print(f"AI: [Error: {e}]")
    
    # Turn it back on
    persona.show_retrieval = True
    print("\n🔊 Turned retrieval visibility back on")
    
    print("\n💬 Same question with retrieval process shown:")
    try:
        response = persona.chat("What have I told you about my machine learning projects?", learn=False)
        print(f"AI: {response}")
    except Exception as e:
        print(f"AI: [Error: {e}]")
    
    # Step 5: Advanced search patterns
    print("\n" + "=" * 50)
    print("Step 5: Advanced Search Patterns")
    print("-" * 40)
    
    # Search for specific combinations
    advanced_searches = [
        ("project AND Python", "Projects involving Python"),
        ("deep learning OR computer vision", "AI/ML related discussions"),
        ("feature engineering", "Data preprocessing topics"),
        ("PyTorch TensorFlow", "Deep learning frameworks")
    ]
    
    for search_term, description in advanced_searches:
        print(f"\n🔍 {description}: '{search_term}'")
        try:
            results = persona.search(search_term)
            if results:
                print(f"  Found {len(results)} conversations:")
                for i, result in enumerate(results[:2], 1):
                    summary = result.get('summary', 'No summary')
                    timestamp = result.get('timestamp', 'Unknown time')
                    print(f"    {i}. [{timestamp}] {summary[:80]}...")
            else:
                print("  No matches found.")
        except Exception as e:
            print(f"  Search error: {e}")
    
    # Step 6: Memory integration with retrieval
    print("\n" + "=" * 50)
    print("Step 6: Memory Integration with Retrieval")
    print("-" * 40)
    
    print("📋 Current memory state:")
    memory = persona.get_memory()
    for key, values in memory.items():
        if values:
            print(f"  {key.upper()}: {len(values)} items")
    
    print("\n🔄 How retrieval enhances memory-based responses:")
    integration_questions = [
        "Based on everything I've told you, what would you recommend for my next learning goal?",
        "How can I apply my machine learning experience to my personal computer vision project?"
    ]
    
    for i, question in enumerate(integration_questions, 1):
        print(f"\n[Integration Question {i}]")
        print(f"You: {question}")
        
        try:
            response = persona.chat(question, learn=False)
            print(f"AI: {response}")
        except Exception as e:
            print(f"AI: [Error: {e}]")
    
    # Cleanup
    persona.close()
    
    print("\n" + "=" * 50)
    print("✅ Conversation Retrieval Demo Complete!")
    print("=" * 50)
    print("\n💡 What you've learned:")
    print("  • How conversations are automatically recorded and stored")
    print("  • How to search through conversation history")
    print("  • How retrieval enhances AI responses with context")
    print("  • How to control retrieval visibility")
    print("  • How memory and retrieval work together")
    print("\n🎯 Key insights:")
    print("  • Retrieval happens automatically during conversations")
    print("  • Search supports simple keywords and phrases")
    print("  • Retrieved context helps AI give more personalized responses")
    print("  • Memory stores facts, retrieval provides conversation context")
    print("\n🎯 Next steps:")
    print("  • Try example 04 for different feature combinations")
    print("  • Check example 05 for advanced usage patterns")


def main():
    """Main function"""
    try:
        demo_conversation_retrieval()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 