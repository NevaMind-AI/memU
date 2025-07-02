#!/usr/bin/env python3
"""
PersonaLab Example 06: Custom LLM Integration
=============================================

This example demonstrates how to integrate custom LLM providers and implement
sophisticated LLM function patterns with PersonaLab.

You'll learn how to:
- Create custom LLM functions from scratch
- Integrate existing local LLMs (like Ollama)
- Build template-based response systems
- Implement fallback and retry mechanisms
- Create domain-specific LLM behaviors
- Handle streaming and async responses

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Optional: Install local LLM runners like Ollama for local testing
"""

import os
import time
import random
import json
from typing import Dict, List, Any, Optional
from personalab import Persona
from personalab.llm import CustomLLMClient


def demo_basic_custom_llm():
    """Demonstrate basic custom LLM implementation"""
    print("🔧 Basic Custom LLM Demo")
    print("=" * 50)
    
    # Simple rule-based LLM
    def simple_rule_llm(messages, **kwargs):
        user_msg = messages[-1]['content'].lower()
        
        # Simple pattern matching
        if any(greeting in user_msg for greeting in ['hello', 'hi', 'hey']):
            return "Hello! I'm a simple rule-based AI assistant. How can I help you today?"
        
        elif any(word in user_msg for word in ['weather', 'temperature']):
            return "I don't have access to real-time weather data, but I can help you with weather-related questions!"
        
        elif any(word in user_msg for word in ['time', 'date']):
            return f"I don't have real-time capabilities, but I can help with time-related calculations."
        
        elif '?' in user_msg:
            return "That's an interesting question! Let me think about how to help you with that."
        
        else:
            return f"I understand you said: '{messages[-1]['content']}'. How can I assist you further?"
    
    print("💡 Creating persona with simple rule-based LLM...")
    rule_client = CustomLLMClient(llm_function=simple_rule_llm)
    persona = Persona(
        agent_id="rule_based_user",
        llm_client=rule_client,
        use_memory=True,
        use_memo=True
    )
    
    test_messages = [
        "Hello there!",
        "What's the weather like today?",
        "What time is it?",
        "Can you help me with Python programming?",
        "I'm working on a machine learning project."
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n[{i}] You: {msg}")
        response = persona.chat(msg)
        print(f"[{i}] AI: {response}")
    
    persona.close()
    print("\n" + "=" * 50 + "\n")


def demo_template_based_llm():
    """Demonstrate template-based LLM responses"""
    print("📝 Template-Based LLM Demo")
    print("=" * 50)
    
    # Response templates
    templates = {
        'greeting': [
            "Hello! I'm {name}, your AI assistant. How can I help you today?",
            "Hi there! {name} here, ready to assist you.",
            "Greetings! I'm {name}. What would you like to know?"
        ],
        'question': [
            "That's a great question about {topic}. Let me help you with that.",
            "Interesting question regarding {topic}. Here's what I think...",
            "Good question about {topic}! I'd be happy to explain."
        ],
        'learning': [
            "I'm learning that you're interested in {topic}. I'll remember this!",
            "Thanks for sharing your interest in {topic}. This helps me understand you better.",
            "I see you're working with {topic}. I'll keep this in mind for future conversations."
        ],
        'default': [
            "I understand you mentioned {content}. Can you tell me more?",
            "Thanks for sharing that about {content}. How can I help?",
            "Interesting point about {content}. What would you like to know?"
        ]
    }
    
    def template_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content']
        user_msg_lower = user_msg.lower()
        
        # Extract topic keywords
        topic_keywords = ['python', 'programming', 'data science', 'machine learning', 
                         'ai', 'coding', 'development', 'software', 'technology']
        
        detected_topic = None
        for keyword in topic_keywords:
            if keyword in user_msg_lower:
                detected_topic = keyword
                break
        
        # Choose template category
        if any(greeting in user_msg_lower for greeting in ['hello', 'hi', 'hey']):
            category = 'greeting'
            template = random.choice(templates[category])
            return template.format(name="TemplateBot")
        
        elif '?' in user_msg:
            category = 'question'
            template = random.choice(templates[category])
            return template.format(topic=detected_topic or "that topic")
        
        elif detected_topic:
            category = 'learning'
            template = random.choice(templates[category])
            return template.format(topic=detected_topic)
        
        else:
            category = 'default'
            template = random.choice(templates[category])
            return template.format(content=user_msg[:30] + "..." if len(user_msg) > 30 else user_msg)
    
    print("🎭 Creating persona with template-based responses...")
    template_client = CustomLLMClient(llm_function=template_llm_function)
    persona = Persona(
        agent_id="template_user",
        llm_client=template_client,
        use_memory=True,
        use_memo=False  # Focus on templates, not retrieval
    )
    
    test_conversations = [
        "Hello!",
        "What is Python programming?",
        "I'm learning machine learning.",
        "Can you help with data science projects?",
        "I work with AI systems at my company."
    ]
    
    for i, msg in enumerate(test_conversations, 1):
        print(f"\n[{i}] You: {msg}")
        response = persona.chat(msg)
        print(f"[{i}] AI: {response}")
    
    # Show memory to see what was learned
    print("\n📋 Memory Summary:")
    memory = persona.get_memory()
    for key, values in memory.items():
        if values:
            print(f"  {key}: {len(values)} items")
    
    persona.close()
    print("\n" + "=" * 50 + "\n")


def demo_domain_specific_llm():
    """Demonstrate domain-specific LLM behavior"""
    print("🎯 Domain-Specific LLM Demo")
    print("=" * 50)
    
    # Specialized LLM for programming assistance
    class ProgrammingAssistantLLM:
        def __init__(self):
            self.knowledge_base = {
                'python': {
                    'concepts': ['variables', 'functions', 'classes', 'modules', 'exceptions'],
                    'frameworks': ['django', 'flask', 'fastapi', 'pandas', 'numpy'],
                    'tips': ['Use list comprehensions for better performance', 'Follow PEP 8 style guide']
                },
                'javascript': {
                    'concepts': ['variables', 'functions', 'promises', 'async/await', 'closures'],
                    'frameworks': ['react', 'vue', 'angular', 'node.js', 'express'],
                    'tips': ['Use const/let instead of var', 'Handle promises properly']
                },
                'data_science': {
                    'concepts': ['data cleaning', 'visualization', 'statistics', 'modeling'],
                    'tools': ['pandas', 'matplotlib', 'seaborn', 'scikit-learn', 'jupyter'],
                    'tips': ['Always explore your data first', 'Validate your models properly']
                }
            }
        
        def identify_domain(self, message):
            """Identify the programming domain from the message"""
            message_lower = message.lower()
            
            if any(word in message_lower for word in ['python', 'py', 'pandas', 'numpy']):
                return 'python'
            elif any(word in message_lower for word in ['javascript', 'js', 'react', 'node']):
                return 'javascript'
            elif any(word in message_lower for word in ['data', 'analysis', 'statistics', 'ml']):
                return 'data_science'
            else:
                return 'general'
        
        def generate_domain_response(self, domain, message):
            """Generate domain-specific response"""
            if domain == 'general':
                return "I'm a programming assistant. I can help with Python, JavaScript, and Data Science. What would you like to know?"
            
            domain_info = self.knowledge_base.get(domain, {})
            
            response_parts = [
                f"Great question about {domain}!"
            ]
            
            # Add relevant concepts
            if 'concepts' in domain_info:
                concepts = ', '.join(domain_info['concepts'][:3])
                response_parts.append(f"Key concepts in {domain} include: {concepts}.")
            
            # Add frameworks/tools
            if 'frameworks' in domain_info:
                tools = ', '.join(domain_info['frameworks'][:3])
                response_parts.append(f"Popular tools/frameworks: {tools}.")
            elif 'tools' in domain_info:
                tools = ', '.join(domain_info['tools'][:3])
                response_parts.append(f"Essential tools: {tools}.")
            
            # Add a tip
            if 'tips' in domain_info and domain_info['tips']:
                tip = random.choice(domain_info['tips'])
                response_parts.append(f"Pro tip: {tip}")
            
            return " ".join(response_parts)
        
        def __call__(self, messages, **kwargs):
            user_msg = messages[-1]['content']
            domain = self.identify_domain(user_msg)
            
            return self.generate_domain_response(domain, user_msg)
    
    print("👨‍💻 Creating programming assistant LLM...")
    programming_llm = ProgrammingAssistantLLM()
    programming_client = CustomLLMClient(llm_function=programming_llm)
    persona = Persona(
        agent_id="programming_assistant",
        llm_client=programming_client,
        use_memory=True,
        use_memo=True
    )
    
    programming_questions = [
        "I want to learn Python programming.",
        "How do I get started with JavaScript development?",
        "What tools do I need for data science projects?",
        "Can you recommend Python frameworks for web development?",
        "I'm working on a machine learning project with pandas."
    ]
    
    for i, question in enumerate(programming_questions, 1):
        print(f"\n[{i}] You: {question}")
        response = persona.chat(question)
        print(f"[{i}] AI: {response}")
    
    # Show specialized memory
    print("\n🧠 Specialized Memory Content:")
    memory = persona.get_memory()
    for key, values in memory.items():
        if values:
            print(f"  {key}: {len(values)} items")
            for item in values[:2]:  # Show first 2 items
                print(f"    • {item}")
    
    persona.close()
    print("\n" + "=" * 50 + "\n")


def main():
    """Main function"""
    print("🛠️  PersonaLab Custom LLM Integration")
    print("=" * 50)
    print("This demo showcases various custom LLM implementation patterns.\n")
    
    try:
        # Run all custom LLM demos
        demo_basic_custom_llm()
        demo_template_based_llm()
        demo_domain_specific_llm()
        
        print("✅ Custom LLM Integration Demo Complete!")
        print("=" * 50)
        print("\n💡 Custom LLM Patterns Learned:")
        print("  • Basic rule-based LLM implementation")
        print("  • Template-based response generation")
        print("  • Domain-specific behavior specialization")
        print("\n🎯 Implementation Guidelines:")
        print("  • Start simple: rule-based responses work well")
        print("  • Use templates for consistent responses")
        print("  • Specialize for specific domains/use cases")
        print("  • Test different patterns thoroughly")
        print("\n🔗 Integration Options:")
        print("  • Local LLMs (Ollama, GPT4All, etc.)")
        print("  • Custom API endpoints")
        print("  • Hybrid rule-based + ML systems")
        print("  • Domain-specific fine-tuned models")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 