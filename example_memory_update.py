#!/usr/bin/env python3
"""
Example: Memory Update with LLM Pipeline

This example demonstrates how to use the simplified memory update pipeline
to analyze conversations and update user profiles and events.
"""

import os
from personalab.memory import Memory, MemoryUpdatePipeline
from personalab.llm import create_llm_client

def example_memory_update():
    """Complete example of memory update process"""
    
    print("=== PersonaLab Memory Update Example ===\n")
    
    # 1. Create initial memory
    print("1. Creating initial memory...")
    memory = Memory("user_123")
    memory.update_profile("用户是一名程序员，对人工智能感兴趣")
    memory.update_events(["用户询问了关于机器学习的问题"])
    
    print(f"Initial profile: {memory.get_profile_content()}")
    print(f"Initial events: {memory.get_event_content()}")
    print()
    
    # 2. Create LLM client (using environment variables for API key)
    print("2. Setting up LLM client...")
    try:
        llm_client = create_llm_client(
            provider="openai",
            api_key=os.getenv("OPENAI_API_KEY"),  # Set this in your environment
            model="gpt-3.5-turbo"
        )
        print("✓ LLM client created successfully")
    except Exception as e:
        print(f"⚠️  LLM client creation failed: {e}")
        print("💡 You can still see the example structure without actual LLM calls")
        llm_client = None
    print()
    
    # 3. Create memory update pipeline
    print("3. Creating memory update pipeline...")
    pipeline = MemoryUpdatePipeline(
        llm_client=llm_client,
        temperature=0.3,
        max_tokens=1500
    )
    print("✓ Pipeline created")
    print()
    
    # 4. Simulate a conversation
    print("4. Simulating conversation...")
    conversation = [
        {
            "role": "user", 
            "content": "我最近在学习深度学习，特别是transformer架构。我在一家互联网公司工作，主要做后端开发。"
        },
        {
            "role": "assistant", 
            "content": "很棒！transformer是现代NLP的核心技术。你在后端开发方面有什么具体的技术栈偏好吗？"
        },
        {
            "role": "user", 
            "content": "我主要用Python和Go，最近在研究如何将AI模型集成到生产环境中。"
        },
        {
            "role": "assistant", 
            "content": "Python和Go都是很好的选择。模型部署确实是个重要话题，涉及性能优化、监控等方面。"
        }
    ]
    
    for i, msg in enumerate(conversation, 1):
        print(f"   {i}. {msg['role']}: {msg['content'][:50]}...")
    print()
    
    # 5. Update memory using pipeline
    print("5. Updating memory with pipeline...")
    
    if llm_client:
        try:
            # This will call all three stages: modification -> update -> theory of mind
            new_memory, pipeline_result = pipeline.update_with_pipeline(
                previous_memory=memory,
                session_conversation=conversation
            )
            
            print("✓ Memory update completed successfully!")
            print()
            
            # 6. Show results
            print("=== PIPELINE RESULTS ===")
            
            print("6a. Modification Stage Result:")
            print(f"Raw LLM analysis:\n{pipeline_result.modification_result}")
            print()
            
            print("6b. Update Stage Result:")
            print(f"Profile updated: {pipeline_result.update_result.profile_updated}")
            print(f"New profile content:\n{new_memory.get_profile_content()}")
            print(f"New events: {new_memory.get_event_content()}")
            print()
            
            print("6c. Theory of Mind Result:")
            print(f"ToM insights:\n{pipeline_result.tom_result.insights}")
            print(f"Confidence score: {pipeline_result.tom_result.confidence_score}")
            print()
            
            print("6d. Complete Memory State:")
            print(new_memory.to_prompt())
            
            # 7. Show metadata
            print("=== METADATA ===")
            print(f"Pipeline metadata: {pipeline_result.pipeline_metadata}")
            print(f"Memory ToM metadata: {new_memory.tom_metadata}")
            
        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            print("This is expected if no LLM client is configured")
    
    else:
        print("⚠️  Skipping pipeline execution (no LLM client)")
        print("💡 To run with actual LLM:")
        print("   export OPENAI_API_KEY='your-api-key'")
        print("   python example_memory_update.py")

def example_manual_stages():
    """Example showing manual execution of individual pipeline stages"""
    
    print("\n" + "="*50)
    print("=== MANUAL STAGE EXECUTION EXAMPLE ===")
    print()
    
    memory = Memory("user_456")
    memory.update_profile("Software engineer interested in AI")
    
    conversation = [
        {"role": "user", "content": "I'm working on a machine learning project"},
        {"role": "assistant", "content": "That sounds interesting! What kind of ML project?"}
    ]
    
    # Example without actual LLM (will raise exceptions)
    pipeline = MemoryUpdatePipeline()
    
    print("Example of individual stage calls:")
    print("1. pipeline.llm_modification_stage(memory, conversation)  # Returns str")
    print("2. pipeline.llm_update_stage(memory, modification_result)  # Returns UpdateResult") 
    print("3. pipeline.llm_theory_of_mind_stage(update_result, conversation)  # Returns ToMResult")
    print()
    print("Each stage will raise an exception if no LLM client is provided")
    print("This ensures immediate feedback when configuration is missing")

if __name__ == "__main__":
    example_memory_update()
    example_manual_stages() 