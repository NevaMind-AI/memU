#!/usr/bin/env python3
"""
Pipeline Debug Example

Shows detailed output from each stage of the memory update pipeline.
"""

from personalab.memory import Memory, MemoryUpdatePipeline
from personalab.llm import create_llm_client
from personalab.config import config
import json


def debug_pipeline_stages():
    """Debug example showing each pipeline stage result"""
    
    print("=== Pipeline Stage-by-Stage Debug ===\n")
    
    # 1. Setup
    print("1. Initial Setup")
    memory = Memory("debug_user")
    memory.update_profile("用户是一名Python开发者，对AI技术感兴趣")
    memory.update_events(["用户询问了关于机器学习的问题", "用户提到想学习深度学习"])
    
    print(f"Initial Profile: {memory.get_profile_content()}")
    print(f"Initial Events: {memory.get_event_content()}")
    print()
    
    # 2. Create pipeline
    print("2. Pipeline Setup")
    try:
        if config.validate_llm_config("openai"):
            llm_client = create_llm_client("openai", **config.get_llm_config("openai"))
            pipeline = MemoryUpdatePipeline(llm_client)
            print("✓ LLM client configured")
        else:
            raise Exception("No API key configured")
    except Exception as e:
        print(f"⚠️ Using mock pipeline (no LLM): {e}")
        pipeline = MemoryUpdatePipeline()
    print()
    
    # 3. Test conversation
    conversation = [
        {"role": "user", "content": "我最近在研究transformer模型，特别是BERT和GPT的区别"},
        {"role": "assistant", "content": "很好的研究方向！BERT是双向编码器，GPT是自回归生成模型"},
        {"role": "user", "content": "我在用PyTorch实现一个简单的transformer，遇到了一些attention机制的问题"},
        {"role": "assistant", "content": "attention机制确实是关键部分，你具体遇到了什么问题？"},
        {"role": "user", "content": "主要是多头注意力的计算，我不确定head dimension的设置"}
    ]
    
    print("3. Test Conversation:")
    for i, msg in enumerate(conversation, 1):
        role_color = "👤" if msg["role"] == "user" else "🤖"
        print(f"   {role_color} {msg['role']}: {msg['content']}")
    print()
    
    # Execute stages individually with detailed output
    try:
        print("="*60)
        print("STAGE 1: LLM MODIFICATION ANALYSIS")
        print("="*60)
        
        modification_result = pipeline.llm_modification_stage(memory, conversation)
        
        print("📋 Stage 1 Result (str):")
        print(f"Type: {type(modification_result)}")
        print(f"Content:\n{modification_result}")
        print(f"Length: {len(modification_result) if modification_result else 0} characters")
        print()
        
        print("="*60)
        print("STAGE 2: LLM MEMORY UPDATE")
        print("="*60)
        
        update_result = pipeline.llm_update_stage(memory, modification_result)
        
        print("📋 Stage 2 Result (UpdateResult):")
        print(f"Type: {type(update_result)}")
        print(f"Profile Updated: {update_result.profile_updated}")
        print(f"New Profile Content:\n{update_result.profile.get_content()}")
        print(f"New Events: {update_result.events.get_content()}")
        print(f"Raw LLM Response Length: {len(update_result.raw_llm_response)}")
        print(f"Metadata: {update_result.metadata}")
        print()
        
        print("="*60)
        print("STAGE 3: LLM THEORY OF MIND ANALYSIS")
        print("="*60)
        
        tom_result = pipeline.llm_theory_of_mind_stage(update_result, conversation)
        
        print("📋 Stage 3 Result (ToMResult):")
        print(f"Type: {type(tom_result)}")
        print(f"Insights Type: {type(tom_result.insights)}")
        print(f"Insights Content:\n{tom_result.insights}")
        print(f"Confidence Score: {tom_result.confidence_score}")
        print(f"Raw LLM Response Length: {len(tom_result.raw_llm_response)}")
        print(f"Metadata: {tom_result.metadata}")
        print()
        
        print("="*60)
        print("FINAL MEMORY STATE")
        print("="*60)
        
        # Create final memory
        new_memory = pipeline._create_updated_memory(memory, update_result, tom_result)
        
        print("📋 Final Memory:")
        print(f"Profile: {new_memory.get_profile_content()}")
        print(f"Events: {new_memory.get_event_content()}")
        print(f"ToM Metadata: {new_memory.tom_metadata}")
        print()
        
        print("📊 COMPARISON:")
        print("Before → After")
        print(f"Profile length: {len(memory.get_profile_content())} → {len(new_memory.get_profile_content())}")
        print(f"Event count: {len(memory.get_event_content())} → {len(new_memory.get_event_content())}")
        print(f"Has ToM data: {memory.tom_metadata is not None} → {new_memory.tom_metadata is not None}")
        
    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        print("This is expected if no LLM client is configured")
        print()
        print("To run with actual LLM processing:")
        print("1. Set up your .env file with OPENAI_API_KEY")
        print("2. Run: python setup_env.py")


def debug_complete_pipeline():
    """Debug the complete pipeline execution"""
    
    print("\n" + "="*60)
    print("COMPLETE PIPELINE EXECUTION")
    print("="*60)
    
    memory = Memory("complete_test")
    memory.update_profile("测试用户")
    
    conversation = [
        {"role": "user", "content": "我想学习自然语言处理"},
        {"role": "assistant", "content": "NLP是很有趣的领域！"}
    ]
    
    try:
        if config.validate_llm_config("openai"):
            llm_client = create_llm_client("openai", **config.get_llm_config("openai"))
            pipeline = MemoryUpdatePipeline(llm_client)
            
            print("🚀 Executing complete pipeline...")
            new_memory, pipeline_result = pipeline.update_with_pipeline(memory, conversation)
            
            print("\n📋 COMPLETE PIPELINE RESULT:")
            print(f"Type: {type(pipeline_result)}")
            print()
            
            print("🔄 Modification Result:")
            print(f"  Content: {pipeline_result.modification_result}")
            print()
            
            print("📝 Update Result:")
            print(f"  Profile Updated: {pipeline_result.update_result.profile_updated}")
            print(f"  New Profile: {new_memory.get_profile_content()}")
            print()
            
            print("🧠 ToM Result:")
            print(f"  Insights: {pipeline_result.tom_result.insights}")
            print(f"  Confidence: {pipeline_result.tom_result.confidence_score}")
            print()
            
            print("🔧 Pipeline Metadata:")
            for key, value in pipeline_result.pipeline_metadata.items():
                print(f"  {key}: {value}")
                
        else:
            print("⚠️ No LLM configuration found")
            
    except Exception as e:
        print(f"❌ Complete pipeline failed: {e}")


if __name__ == "__main__":
    debug_pipeline_stages()
    debug_complete_pipeline() 