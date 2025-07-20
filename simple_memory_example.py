#!/usr/bin/env python3
"""
智能Memory Agent使用示例 - 结构化工作流程

展示Memory Agent的新结构化工作流程：
1. 总结对话 → 提取distinct memory items
2. 存储memory items和总结到activity
3. 获取可用categories
4. 生成memory建议
5. 根据建议更新各categories (返回结构化格式)
6. 链接相关memories
"""

from memu.llm import OpenAIClient
from memu.memory import MemoryAgent

def main():
    # 1. 初始化LLM客户端
    llm_client = OpenAIClient(model="gpt-4o-mini")
    
    # 2. 初始化Memory Agent
    memory_agent = MemoryAgent(
        llm_client=llm_client,
        memory_dir="memory"
    )
    
    # 3. 示例对话
    conversation = [
        {"role": "user", "content": "你好！我是张三，今年25岁，是一名软件工程师。"},
        {"role": "assistant", "content": "你好张三！很高兴认识你。软件工程师是很有趣的职业。"},
        {"role": "user", "content": "是的，我在一家AI公司工作，主要做机器学习算法开发。明天我要参加一个技术会议。"},
        {"role": "assistant", "content": "听起来很棒！AI和机器学习是很前沿的领域。技术会议应该会很有收获。"},
        {"role": "user", "content": "对了，我最近在学习深度学习，特别对计算机视觉很感兴趣。下个月要参加公司的年会。我喜欢在业余时间阅读和跑步。"},
        {"role": "assistant", "content": "计算机视觉是AI领域很有前景的方向！公司年会一定很有意思。阅读和跑步都是很好的爱好。"}
    ]
    
    print("🧠 Memory Agent 结构化工作流程演示")
    print("=" * 60)
    print(f"💬 对话长度: {len(conversation)} 条消息")
    print()
    print("🤖 LLM将按照以下结构化流程处理：")
    print("   1. 总结对话 → 提取多个distinct memory items")
    print("   2. 存储memory items和总结到activity category")
    print("   3. 获取可用的memory categories")
    print("   4. 为memory items生成category建议")
    print("   5. 根据建议更新各categories (返回结构化格式)")
    print("   6. 为修改过的memories链接相关记忆")
    print()
    
    # 4. 执行结构化工作流程
    result = memory_agent.run(
        conversation=conversation,
        character_name="张三"
    )
    
    # 5. 分析和展示结果
    print("📊 处理结果分析:")
    print("=" * 60)
    
    if result["success"]:
        print("✅ 处理成功！")
        print(f"🔄 迭代次数: {result['iterations']}")
        print(f"🔧 函数调用次数: {len(result['function_calls'])}")
        print(f"📁 生成文件数: {len(result['files_generated'])}")
        
        print(f"\n📁 生成的文件:")
        for file_path in result['files_generated']:
            print(f"   📄 {file_path}")
        
        print(f"\n🔧 结构化工作流程追踪:")
        workflow_steps = {
            "summarize_conversation": "📊 步骤1: 总结对话并提取memory items",
            "add_memory": "📝 步骤2: 存储memory items到activity",
            "get_available_categories": "📂 步骤3: 获取可用categories", 
            "generate_memory_suggestions": "💡 步骤4: 生成category建议",
            "update_memory_with_suggestions": "🔄 步骤5: 更新categories (结构化格式)",
            "link_related_memories": "🔗 步骤6: 链接相关memories"
        }
        
        step_counts = {}
        for call in result['function_calls']:
            func_name = call['function']
            if func_name not in step_counts:
                step_counts[func_name] = 0
            step_counts[func_name] += 1
            
            status = "✅" if call['result'].get('success') else "❌"
            step_desc = workflow_steps.get(func_name, f"🔧 {func_name}")
            
            # 显示特殊信息
            if func_name == "summarize_conversation":
                items_count = call['result'].get('items_count', 0)
                print(f"   {status} {step_desc} - {items_count} memory items extracted")
            elif func_name == "update_memory_with_suggestions":
                modifications = call['result'].get('modifications', [])
                category = call['arguments'].get('category', 'unknown')
                print(f"   {status} {step_desc} - {category} ({len(modifications)} modifications)")
            elif func_name == "generate_memory_suggestions":
                suggestions = call['result'].get('suggestions', {})
                print(f"   {status} {step_desc} - {len(suggestions)} categories analyzed")
            else:
                category = call['arguments'].get('category', '')
                if category:
                    print(f"   {status} {step_desc} - {category}")
                else:
                    print(f"   {status} {step_desc}")
        
        print(f"\n📊 工作流程统计:")
        for func_name, count in step_counts.items():
            step_desc = workflow_steps.get(func_name, func_name)
            print(f"   • {step_desc}: {count}次")
        
        print(f"\n📝 详细处理日志:")
        for log_entry in result['processing_log'][-5:]:  # 显示最后5条日志
            print(f"   • {log_entry}")
            
        # 查找结构化的modifications
        structured_modifications = []
        for call in result['function_calls']:
            if call['function'] == "update_memory_with_suggestions":
                modifications = call['result'].get('modifications', [])
                structured_modifications.extend(modifications)
        
        if structured_modifications:
            print(f"\n📋 结构化Memory修改 ({len(structured_modifications)}条):")
            for i, mod in enumerate(structured_modifications[:3], 1):  # 显示前3条
                print(f"   {i}. Memory ID: {mod['memory_id']}")
                print(f"      Category: {mod['category']}")
                print(f"      Content: {mod['content'][:80]}...")
                print()
            
    else:
        print(f"❌ 处理失败: {result['error']}")
    
    print(f"\n🎉 演示完成！")
    print("🔍 新结构化工作流程的优势:")
    print("✅ 6步清晰流程，逻辑分明")
    print("✅ 专门的对话总结和memory item提取")
    print("✅ 多memory items同时处理")
    print("✅ 智能建议生成")
    print("✅ 结构化输出便于后续处理")
    print("✅ 自动链接相关记忆")
    print("✅ 完整的处理追踪和错误处理")

if __name__ == "__main__":
    main() 