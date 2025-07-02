#!/usr/bin/env python3
"""
01_basic_memory.py

PersonaLab基础内存管理示例

演示如何：
1. 创建和管理AI代理的内存
2. 更新profile、events和Theory of Mind
3. 基本的内存操作
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memory import MemoryClient


def main():
    print("=== PersonaLab 基础内存管理示例 ===\n")
    
    # 1. 创建内存管理器
    print("1. 创建内存管理器...")
    memory_manager = MemoryClient(
        db_path="basic_memory_demo.db"
    )
    print("✅ 内存管理器创建成功\n")
    
    # 2. 获取或创建代理内存
    print("2. 创建AI代理内存...")
    agent_id = "learning_assistant"
    memory = memory_manager.get_memory_by_agent(agent_id)
    
    print(f"✅ 代理内存创建成功")
    print(f"   代理ID: {agent_id}")
    print(f"   内存ID: {memory.memory_id}")
    print()
    
    # 3. 设置初始profile
    print("3. 设置初始profile...")
    initial_profile = "我是一个学习助手AI，专门帮助用户学习编程和技术知识。"
    memory.update_profile(initial_profile)
    
    print(f"✅ Profile设置完成")
    print(f"   内容: {memory.get_profile_content()}")
    print()
    
    # 4. 添加事件记录
    print("4. 添加事件记录...")
    events = [
        "用户询问了Python基础知识",
        "推荐了Python学习资源",
        "用户对机器学习表现出兴趣",
        "提供了数据科学的入门指导"
    ]
    
    for event in events:
        memory.update_events([event])
        print(f"   ✅ 添加事件: {event}")
    
    print(f"\n所有事件:")
    for i, event in enumerate(memory.get_event_content(), 1):
        print(f"   {i}. {event}")
    print()
    
    # 5. 添加Theory of Mind洞察
    print("5. 添加Theory of Mind洞察...")
    tom_insights = [
        "用户是编程初学者，需要基础指导",
        "用户学习积极主动，喜欢实践",
        "用户对AI和机器学习领域有浓厚兴趣"
    ]
    
    for insight in tom_insights:
        memory.update_mind([insight])
        print(f"   ✅ 添加洞察: {insight}")
    
    print(f"\n所有洞察:")
    for i, insight in enumerate(memory.get_mind_content(), 1):
        print(f"   {i}. {insight}")
    print()
    
    # 6. 查看完整内存状态
    print("6. 完整内存状态...")
    print("=" * 50)
    print(memory.to_prompt())
    print("=" * 50)
    print()
    
    # 7. 更新profile信息
    print("7. 更新profile信息...")
    updated_profile = "我是一个学习助手AI，专门帮助用户学习编程和技术知识。我特别擅长Python、机器学习和数据科学领域的指导。"
    memory.update_profile(updated_profile)
    
    print(f"✅ Profile更新完成")
    print(f"   新内容: {memory.get_profile_content()}")
    print()
    
    # 8. 保存内存到数据库
    print("8. 保存内存...")
    success = memory_manager.database.save_memory(memory)
    
    if success:
        print("✅ 内存保存成功")
    else:
        print("❌ 内存保存失败")
    
    # 9. 从数据库重新加载
    print("\n9. 重新加载内存...")
    reloaded_memory = memory_manager.get_memory_by_agent(agent_id)
    
    print("✅ 内存重新加载成功")
    print(f"   Profile: {reloaded_memory.get_profile_content()[:50]}...")
    print(f"   事件数量: {len(reloaded_memory.get_event_content())}")
    print(f"   洞察数量: {len(reloaded_memory.get_mind_content())}")
    
    # 10. 清理
    print("\n10. 清理资源...")
    memory_manager.database.close()
    print("✅ 资源清理完成")
    
    print("\n=== 示例完成 ===")
    print("\n💡 学到的知识点:")
    print("1. ✅ 如何创建和管理AI代理内存")
    print("2. ✅ 如何更新profile、events和ToM")
    print("3. ✅ 如何保存和加载内存状态")
    print("4. ✅ 内存数据的持久化存储")


if __name__ == "__main__":
    main() 