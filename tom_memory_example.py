#!/usr/bin/env python3
"""
ToM Memory Example

Demonstrates the new ToMMemory component with list of string storage.
"""

from personalab.memory import Memory, ToMMemory
from personalab import config


def tom_memory_basic_example():
    """Basic ToMMemory usage example"""
    
    print("=== ToMMemory Basic Usage ===\n")
    
    # 1. Create standalone ToMMemory
    tom_memory = ToMMemory()
    
    print("1. Basic ToMMemory Operations:")
    print(f"Initial insights: {tom_memory.get_content()}")
    print(f"Is empty: {tom_memory.is_empty()}")
    print()
    
    # 2. Add insights
    insights = [
        "用户对技术学习有强烈的动机",
        "用户喜欢深入理解底层原理",
        "用户倾向于实践性学习方式",
        "用户在遇到问题时会主动寻求帮助"
    ]
    
    print("2. Adding insights:")
    for i, insight in enumerate(insights, 1):
        tom_memory.add_insight(insight)
        print(f"   Added insight {i}: {insight}")
    
    print(f"\nCurrent insights: {tom_memory.get_content()}")
    print(f"Insight count: {tom_memory.get_insight_count()}")
    print()
    
    # 3. Search insights
    print("3. Searching insights:")
    tech_insights = tom_memory.search_insights("技术")
    print(f"Tech-related insights: {tech_insights}")
    
    learning_insights = tom_memory.search_insights("学习")
    print(f"Learning-related insights: {learning_insights}")
    print()
    
    # 4. Get recent insights
    print("4. Recent insights:")
    recent = tom_memory.get_recent_insights(2)
    print(f"Last 2 insights: {recent}")
    print()
    
    # 5. Convert to prompt format
    print("5. Prompt format:")
    prompt = tom_memory.to_prompt()
    print(f"ToM prompt:\n{prompt}")


def tom_memory_with_memory_class():
    """ToMMemory integrated with Memory class"""
    
    print("\n" + "="*60)
    print("=== ToMMemory with Memory Class ===\n")
    
    # 1. Create Memory with ToMMemory
    memory = Memory("tom_test_user")
    memory.update_profile("用户是一名AI研究者")
    memory.update_events(["用户询问了transformer原理", "用户实现了注意力机制"])
    
    print("1. Initial Memory State:")
    print(f"Profile: {memory.get_profile_content()}")
    print(f"Events: {memory.get_event_content()}")
    print(f"ToM insights: {memory.get_tom_content()}")
    print()
    
    # 2. Add ToM insights
    tom_insights = [
        "用户具有深厚的技术背景",
        "用户对前沿AI技术保持敏锐的洞察力",
        "用户倾向于理论与实践相结合的学习方式",
        "用户在技术讨论中表现出批判性思维"
    ]
    
    print("2. Adding ToM insights:")
    memory.update_tom(tom_insights)
    
    for insight in tom_insights:
        print(f"   - {insight}")
    print()
    
    # 3. Complete memory prompt
    print("3. Complete Memory Prompt:")
    full_prompt = memory.to_prompt()
    print(full_prompt)
    
    # 4. Memory summary
    print("4. Memory Summary:")
    summary = memory.get_memory_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    # 5. ToMMemory operations
    print("5. ToMMemory Operations:")
    memory.add_tom_insight("用户展现出了优秀的问题分析能力")
    print(f"After adding one more insight: {len(memory.get_tom_content())} insights")
    
    # Search in tom memory
    tech_insights = memory.tom_memory.search_insights("技术")
    print(f"Tech-related insights: {tech_insights}")


def tom_memory_backward_compatibility():
    """Test backward compatibility with tom_metadata"""
    
    print("\n" + "="*60)
    print("=== Backward Compatibility Test ===\n")
    
    memory = Memory("compat_test")
    
    # 1. Test tom_metadata property (getter)
    print("1. Tom_metadata getter (empty):")
    print(f"tom_metadata: {memory.tom_metadata}")
    print()
    
    # 2. Add insights and check tom_metadata
    memory.update_tom(["洞察1", "洞察2", "洞察3"])
    print("2. After adding insights:")
    print(f"tom_memory content: {memory.get_tom_content()}")
    print(f"tom_metadata: {memory.tom_metadata}")
    print()
    
    # 3. Test tom_metadata setter
    print("3. Setting tom_metadata (legacy format):")
    legacy_metadata = {
        "insights": "传统洞察1\n传统洞察2\n传统洞察3",
        "confidence": 0.8
    }
    memory.tom_metadata = legacy_metadata
    
    print(f"After setting legacy metadata:")
    print(f"tom_memory content: {memory.get_tom_content()}")
    print(f"tom_metadata: {memory.tom_metadata}")


def tom_memory_capacity_test():
    """Test ToMMemory capacity management"""
    
    print("\n" + "="*60)
    print("=== ToMMemory Capacity Test ===\n")
    
    # Create ToMMemory with small capacity
    tom_memory = ToMMemory(max_insights=5)
    
    print("1. Adding more insights than capacity (max=5):")
    for i in range(8):
        insight = f"洞察 {i+1}: 这是第{i+1}个心理分析洞察"
        tom_memory.add_insight(insight)
        print(f"   Added: {insight}")
        print(f"   Current count: {tom_memory.get_insight_count()}")
    
    print()
    print("2. Final insights (should only have last 5):")
    for i, insight in enumerate(tom_memory.get_content(), 1):
        print(f"   {i}. {insight}")


if __name__ == "__main__":
    tom_memory_basic_example()
    tom_memory_with_memory_class()
    tom_memory_backward_compatibility()
    tom_memory_capacity_test() 