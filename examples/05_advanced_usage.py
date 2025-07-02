#!/usr/bin/env python3
"""
PersonaLab Example 05: Advanced Usage Patterns
==============================================

This example demonstrates advanced PersonaLab usage patterns and techniques.

You'll learn how to:
- Use different LLM providers (OpenAI, Anthropic, Custom)
- Implement custom LLM functions
- Handle error scenarios gracefully
- Build multi-agent systems
- Implement advanced memory patterns
- Create production-ready implementations

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys:
   - OPENAI_API_KEY="your-openai-key"
   - ANTHROPIC_API_KEY="your-anthropic-key"
"""

import os
import json
import asyncio
from typing import Dict, List, Any
from personalab import Persona


def demo_multiple_llm_providers():
    """Demonstrate using different LLM providers"""
    print("🎭 Multiple LLM Providers Demo")
    print("=" * 50)
    
    # Check available providers
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))
    
    providers = []
    
    if has_openai:
        providers.append(("OpenAI", lambda: Persona(agent_id="openai_test")))
    if has_anthropic:
        from personalab.llm import AnthropicClient
        providers.append(("Anthropic", lambda: Persona(agent_id="anthropic_test", llm_client=AnthropicClient())))
    
    # Always include custom for demo
    def custom_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content']
        return f"Custom LLM response to: '{user_msg}'. This simulates any LLM provider."
    
    from personalab.llm import CustomLLMClient
    providers.append(("Custom", lambda: Persona(
        agent_id="custom_test", 
        llm_client=CustomLLMClient(llm_function=custom_llm_function)
    )))
    
    test_message = "What's the capital of France?"
    
    for provider_name, create_persona in providers:
        print(f"\n🤖 Testing {provider_name} Provider:")
        try:
            persona = create_persona()
            response = persona.chat(test_message, learn=False)
            print(f"  Response: {response[:100]}...")
            persona.close()
            print(f"  ✅ {provider_name} working correctly")
        except Exception as e:
            print(f"  ❌ {provider_name} error: {e}")
    
    print("\n" + "=" * 50 + "\n")


def demo_custom_llm_patterns():
    """Demonstrate advanced custom LLM patterns"""
    print("🛠️  Custom LLM Patterns Demo")
    print("=" * 50)
    
    # Pattern 1: Stateful LLM with memory
    print("📊 Pattern 1: Stateful LLM with Memory")
    class StatefulLLM:
        def __init__(self):
            self.call_count = 0
            self.conversation_history = []
        
        def __call__(self, messages, **kwargs):
            self.call_count += 1
            user_msg = messages[-1]['content']
            self.conversation_history.append(user_msg)
            
            return f"[Call #{self.call_count}] I remember {len(self.conversation_history)} messages from you. Latest: '{user_msg}'"
    
    stateful_llm = StatefulLLM()
    stateful_client = CustomLLMClient(llm_function=stateful_llm)
    persona1 = Persona(
        agent_id="stateful_test",
        llm_client=stateful_client,
        use_memory=False  # LLM handles its own state
    )
    
    for i in range(3):
        response = persona1.chat(f"Message {i+1}", learn=False)
        print(f"  Turn {i+1}: {response}")
    persona1.close()
    
    # Pattern 2: Multi-model ensemble
    print("\n🎯 Pattern 2: Multi-Model Ensemble")
    def ensemble_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        
        if 'math' in user_msg or 'calculate' in user_msg:
            return "Math Specialist: I'll solve this mathematical problem for you."
        elif 'code' in user_msg or 'program' in user_msg:
            return "Code Specialist: I'll help you with programming and development."
        elif 'creative' in user_msg or 'story' in user_msg:
            return "Creative Specialist: I'll assist with creative writing and storytelling."
        else:
            return "General Assistant: I can help with a wide range of topics."
    
    ensemble_client = CustomLLMClient(llm_function=ensemble_llm_function)
    persona2 = Persona(
        agent_id="ensemble_test",
        llm_client=ensemble_client
    )
    
    test_queries = [
        "Help me calculate the area of a circle",
        "Write a Python function to sort a list",
        "Tell me a creative story about space",
        "What's the weather like today?"
    ]
    
    for query in test_queries:
        response = persona2.chat(query, learn=False)
        print(f"  Query: {query}")
        print(f"  Response: {response}\n")
    persona2.close()
    
    print("=" * 50 + "\n")


def demo_error_handling():
    """Demonstrate robust error handling"""
    print("🛡️  Error Handling and Resilience Demo")
    print("=" * 50)
    
    # Error simulation function
    def error_prone_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        
        if 'error' in user_msg:
            raise Exception("Simulated LLM API error")
        elif 'timeout' in user_msg:
            raise TimeoutError("Simulated timeout error")
        elif 'rate' in user_msg:
            raise Exception("Rate limit exceeded")
        else:
            return f"Successfully processed: {user_msg}"
    
    error_client = CustomLLMClient(llm_function=error_prone_llm_function)
    persona = Persona(
        agent_id="error_test",
        llm_client=error_client
    )
    
    test_cases = [
        "Normal message",
        "This should cause an error",
        "This will timeout",
        "This hits rate limits",
        "Another normal message"
    ]
    
    for msg in test_cases:
        print(f"\n💬 Testing: '{msg}'")
        try:
            response = persona.chat(msg, learn=False)
            print(f"  ✅ Success: {response}")
        except Exception as e:
            print(f"  ❌ Error caught: {e}")
            print(f"  🔄 Implementing fallback strategy...")
            
            # Fallback strategy
            fallback_response = f"I encountered an issue processing your message: '{msg}'. Please try rephrasing or try again later."
            print(f"  🔧 Fallback: {fallback_response}")
    
    persona.close()
    print("\n" + "=" * 50 + "\n")


def demo_multi_agent_system():
    """Demonstrate multi-agent conversation system"""
    print("👥 Multi-Agent System Demo")
    print("=" * 50)
    
    # Create different agent personalities
    def create_agent_llm(personality):
        def agent_llm_function(messages, **kwargs):
            user_msg = messages[-1]['content']
            
            responses = {
                "analyst": f"Analytical perspective: Let me break down '{user_msg}' systematically...",
                "creative": f"Creative perspective: This sparks an interesting idea about '{user_msg}'...",
                "practical": f"Practical perspective: Here's how to implement '{user_msg}' effectively...",
                "critic": f"Critical perspective: I see potential issues with '{user_msg}'..."
            }
            
            return responses.get(personality, f"Generic response to: {user_msg}")
        
        return agent_llm_function
    
    # Create multiple agents
    agents = {}
    personalities = ["analyst", "creative", "practical", "critic"]
    
    for personality in personalities:
        agent_client = CustomLLMClient(llm_function=create_agent_llm(personality))
        agents[personality] = Persona(
            agent_id=f"{personality}_agent",
            llm_client=agent_client,
            use_memory=True,
            use_memo=True
        )
    
    # Multi-agent discussion
    topic = "Building a mobile app for language learning"
    print(f"🎯 Topic: {topic}\n")
    
    print("💭 Agent Discussion:")
    for personality, agent in agents.items():
        print(f"\n🤖 {personality.upper()} Agent:")
        try:
            response = agent.chat(topic, learn=True)
            print(f"  {response}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Cross-agent memory check
    print("\n🧠 Cross-Agent Memory Analysis:")
    for personality, agent in agents.items():
        memory = agent.get_memory()
        event_count = len(memory.get('events', []))
        print(f"  {personality.upper()}: {event_count} recorded events")
    
    # Cleanup
    for agent in agents.values():
        agent.close()
    
    print("\n" + "=" * 50 + "\n")


def demo_advanced_memory_patterns():
    """Demonstrate advanced memory management patterns"""
    print("🧠 Advanced Memory Patterns Demo")
    print("=" * 50)
    
    def smart_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content']
        return f"I'm processing your message about: {user_msg}. I'll extract and store relevant information."
    
    memory_client = CustomLLMClient(llm_function=smart_llm_function)
    persona = Persona(
        agent_id="memory_expert",
        llm_client=memory_client,
        use_memory=True,
        use_memo=True
    )
    
    # Pattern 1: Structured information storage
    print("📋 Pattern 1: Structured Information Storage")
    structured_info = [
        "My name is Alex Johnson and I'm 28 years old",
        "I work as a Senior Data Scientist at TechCorp",
        "I specialize in computer vision and NLP",
        "I have a PhD in Machine Learning from MIT",
        "I enjoy hiking, photography, and reading sci-fi novels"
    ]
    
    for info in structured_info:
        persona.chat(info)
    
    # Manually add structured facts
    persona.add_memory("User has 5 years of industry experience", memory_type="facts")
    persona.add_memory("User prefers Python over R for data science", memory_type="preferences")
    persona.add_memory("User is working on autonomous vehicle perception systems", memory_type="facts")
    
    # Pattern 2: Memory retrieval and analysis
    print("\n🔍 Pattern 2: Memory Retrieval and Analysis")
    memory = persona.get_memory()
    
    print("📊 Memory Statistics:")
    for category, items in memory.items():
        print(f"  {category}: {len(items)} items")
    
    print("\n📚 Sample Facts:")
    for fact in memory.get('facts', [])[:3]:
        print(f"  • {fact}")
    
    print("\n❤️  Sample Preferences:")
    for pref in memory.get('preferences', [])[:3]:
        print(f"  • {pref}")
    
    # Pattern 3: Contextual memory queries
    print("\n💬 Pattern 3: Contextual Memory Queries")
    context_queries = [
        "What do you know about my educational background?",
        "What are my current work projects?",
        "What are my hobbies and interests?"
    ]
    
    for query in context_queries:
        print(f"\nQ: {query}")
        response = persona.chat(query, learn=False)
        print(f"A: {response}")
    
    persona.close()
    print("\n" + "=" * 50 + "\n")


def demo_production_patterns():
    """Demonstrate production-ready patterns"""
    print("🏭 Production-Ready Patterns Demo")
    print("=" * 50)
    
    # Pattern 1: Configuration-driven setup
    print("⚙️  Pattern 1: Configuration-Driven Setup")
    
    config = {
        "agent_id": "production_bot",
        "use_memory": True,
        "use_memo": True,
        "show_retrieval": False,  # Turn off for production
        "max_memory_items": 100,
        "error_fallback": "I apologize, but I'm experiencing technical difficulties. Please try again."
    }
    
    def production_llm_function(messages, **kwargs):
        # Simulate production LLM with error handling
        user_msg = messages[-1]['content']
        
        try:
            # Simulate processing
            if len(user_msg.strip()) == 0:
                return "I didn't receive any message. Could you please try again?"
            
            return f"Production response: I've processed your message and stored relevant information for future interactions."
            
        except Exception as e:
            return config["error_fallback"]
    
    print(f"📋 Configuration: {json.dumps(config, indent=2)}")
    
    production_client = CustomLLMClient(llm_function=production_llm_function)
    persona = Persona(
        agent_id=config["agent_id"],
        llm_client=production_client,
        use_memory=config["use_memory"],
        use_memo=config["use_memo"],
        show_retrieval=config["show_retrieval"]
    )
    
    # Pattern 2: Input validation and sanitization
    print("\n🛡️  Pattern 2: Input Validation")
    
    test_inputs = [
        "Normal user message",
        "",  # Empty input
        "A" * 1000,  # Very long input
        "Message with special chars: @#$%^&*()",
        None  # Invalid input type
    ]
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n[Test {i}] Input: {str(test_input)[:50]}{'...' if test_input and len(str(test_input)) > 50 else ''}")
        
        try:
            if test_input is None:
                print("  ❌ Invalid input type detected")
                continue
                
            # Input validation
            if not isinstance(test_input, str):
                print("  ❌ Input must be string")
                continue
                
            if len(test_input.strip()) == 0:
                print("  ⚠️  Empty input detected")
                
            if len(test_input) > 500:  # Max length check
                test_input = test_input[:500] + "..."
                print("  ⚠️  Input truncated to max length")
            
            response = persona.chat(test_input, learn=True)
            print(f"  ✅ Response: {response[:100]}...")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Pattern 3: Monitoring and logging
    print("\n📊 Pattern 3: Monitoring and Logging")
    
    # Simulate monitoring
    memory = persona.get_memory()
    stats = {
        "total_conversations": len(memory.get('events', [])),
        "facts_learned": len(memory.get('facts', [])),
        "preferences_stored": len(memory.get('preferences', [])),
        "memory_utilization": sum(len(items) for items in memory.values()) / config.get("max_memory_items", 100) * 100
    }
    
    print("📈 System Statistics:")
    for metric, value in stats.items():
        if metric == "memory_utilization":
            print(f"  {metric}: {value:.1f}%")
        else:
            print(f"  {metric}: {value}")
    
    persona.close()
    print("\n" + "=" * 50 + "\n")


def main():
    """Main function"""
    print("🚀 PersonaLab Advanced Usage Patterns")
    print("=" * 50)
    print("This demo showcases advanced patterns and production-ready techniques.\n")
    
    try:
        # Run all advanced demos
        demo_multiple_llm_providers()
        demo_custom_llm_patterns()
        demo_error_handling()
        demo_multi_agent_system()
        demo_advanced_memory_patterns()
        demo_production_patterns()
        
        print("✅ Advanced Usage Demo Complete!")
        print("=" * 50)
        print("\n💡 Advanced Patterns Learned:")
        print("  • Multi-provider LLM support")
        print("  • Custom LLM function patterns")
        print("  • Robust error handling strategies")
        print("  • Multi-agent system architecture")
        print("  • Advanced memory management")
        print("  • Production-ready implementations")
        print("\n🎯 Production Checklist:")
        print("  • ✅ Input validation and sanitization")
        print("  • ✅ Error handling and fallbacks")
        print("  • ✅ Configuration-driven setup")
        print("  • ✅ Monitoring and logging")
        print("  • ✅ Memory management and limits")
        print("  • ✅ Performance optimization")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 