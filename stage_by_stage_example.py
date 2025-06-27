#!/usr/bin/env python3
"""
Stage-by-Stage Memory Update Example

Shows how to use individual pipeline stages for more control.
"""

from personalab.memory import Memory, MemoryUpdatePipeline
from personalab.llm import create_llm_client

def stage_by_stage_example():
    """Example using individual pipeline stages"""
    
    print("=== Stage-by-Stage Memory Update ===\n")
    
    # Setup
    memory = Memory("user_001") 
    memory.update_profile("用户是一名Python开发者")
    memory.update_events(["用户提到喜欢编程"])
    
    conversation = [
        {"role": "user", "content": "我最近在学习机器学习，用的是PyTorch"},
        {"role": "assistant", "content": "PyTorch是个很好的深度学习框架！"},
        {"role": "user", "content": "是的，我特别喜欢它的动态图特性"}
    ]
    
    # Create pipeline (without LLM for demonstration)
    pipeline = MemoryUpdatePipeline()
    
    print("Initial memory:")
    print(f"Profile: {memory.get_profile_content()}")
    print(f"Events: {memory.get_event_content()}")
    print()
    
    try:
        # Stage 1: Modification Analysis
        print("Stage 1: LLM Modification Analysis")
        modification_result = pipeline.llm_modification_stage(memory, conversation)
        print(f"Result type: {type(modification_result)}")
        print(f"Result: {modification_result}")
        print()
        
        # Stage 2: Memory Update  
        print("Stage 2: LLM Memory Update")
        update_result = pipeline.llm_update_stage(memory, modification_result)
        print(f"Profile updated: {update_result.profile_updated}")
        print(f"New profile: {update_result.profile.get_content()}")
        print(f"New events: {update_result.events.get_content()}")
        print()
        
        # Stage 3: Theory of Mind Analysis
        print("Stage 3: LLM Theory of Mind Analysis")
        tom_result = pipeline.llm_theory_of_mind_stage(update_result, conversation)
        print(f"Insights type: {type(tom_result.insights)}")
        print(f"Insights: {tom_result.insights}")
        print(f"Confidence: {tom_result.confidence_score}")
        
    except Exception as e:
        print(f"Expected error (no LLM client): {e}")
        print()
        print("To run with actual LLM processing:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Modify pipeline creation to include LLM client:")
        print("   llm_client = create_llm_client('openai')")
        print("   pipeline = MemoryUpdatePipeline(llm_client)")

def show_expected_formats():
    """Show expected input/output formats for each stage"""
    
    print("\n" + "="*50)
    print("=== EXPECTED FORMATS ===\n")
    
    print("Stage 1 - llm_modification_stage:")
    print("Input: Memory + List[Dict[str, str]] (conversation)")
    print("Output: str (formatted like this)")
    print("""
profile:
- 用户学习机器学习
- 用户使用PyTorch框架
events:
- 用户提到学习PyTorch
- 用户喜欢动态图特性
""")
    
    print("Stage 2 - llm_update_stage:")  
    print("Input: Memory + str (from stage 1)")
    print("Output: UpdateResult with ProfileMemory and EventMemory")
    print()
    
    print("Stage 3 - llm_theory_of_mind_stage:")
    print("Input: UpdateResult + conversation")
    print("Output: ToMResult with insights as string")
    print("""
推测：
- 用户对深度学习技术有浓厚兴趣
- 用户偏好实用性强的工具
- 用户正在从基础向深度学习转型
""")

if __name__ == "__main__":
    stage_by_stage_example()
    show_expected_formats() 