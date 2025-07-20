#!/usr/bin/env python3
"""
OpenAI官方Function Calling示例

展示如何按照OpenAI最佳实践使用Memory Agent
"""

import json
from memu.llm import OpenAIClient
from memu.memory import MemoryAgent

def main():
    """OpenAI Function Calling最佳实践示例"""
    
    print("🚀 OpenAI官方Function Calling示例")
    print("=" * 50)
    
    # 1. 初始化组件
    llm_client = OpenAIClient(model="gpt-4o-mini")
    memory_agent = MemoryAgent(llm_client=llm_client, memory_dir="memory")
    
    # 2. 获取OpenAI兼容的函数定义
    function_schemas = memory_agent.get_functions_schema()
    
    print(f"📋 可用函数: {len(function_schemas)} 个")
    for schema in function_schemas:
        print(f"  • {schema['name']}: {schema['description']}")
    print()
    
    # 3. 构建对话 - 使用明确的指令触发函数调用
    messages = [
        {
            "role": "system",
            "content": """你是一个智能助手，可以使用记忆功能来存储和检索信息。
            
当用户要求你记住信息时，使用 add_memory 函数。
当用户询问之前的信息时，使用 search_memory 或 read_memory 函数。
当用户要求更新信息时，使用 update_memory 函数。

请根据用户的需求选择合适的函数调用。"""
        },
        {
            "role": "user",
            "content": "请帮我记住：我叫Alice，25岁，是一名产品经理，喜欢阅读和旅行。"
        }
    ]
    
    # 4. 按照OpenAI官方格式调用
    def process_conversation(messages, max_iterations=5):
        """处理对话，支持多轮函数调用"""
        
        for iteration in range(max_iterations):
            print(f"\n🔄 迭代 {iteration + 1}")
            print("-" * 20)
            
            # 调用OpenAI API
            response = llm_client.chat_completion(
                messages=messages,
                tools=[{"type": "function", "function": schema} for schema in function_schemas],
                tool_choice="auto",
                temperature=0.3
            )
            
            if not response.success:
                print(f"❌ API调用失败: {response.error}")
                break
            
            # 添加助手回复到对话历史
            assistant_message = {
                "role": "assistant",
                "content": response.content
            }
            
            # 处理函数调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🛠️ 检测到 {len(response.tool_calls)} 个函数调用")
                
                # 添加函数调用到助手消息
                assistant_message["tool_calls"] = response.tool_calls
                messages.append(assistant_message)
                
                # 执行每个函数调用
                for tool_call in response.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    print(f"  📞 调用: {function_name}")
                    print(f"  📝 参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
                    
                    # 执行函数
                    result = memory_agent.call_function(function_name, arguments)
                    
                    # 添加工具结果到对话历史
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    }
                    messages.append(tool_message)
                    
                    print(f"  ✅ 结果: {'成功' if result.get('success') else '失败'}")
                    if result.get('success'):
                        if 'file_path' in result:
                            print(f"  📁 文件: {result['file_path']}")
                    else:
                        print(f"  ❌ 错误: {result.get('error')}")
                
            else:
                # 没有函数调用，添加回复并结束
                messages.append(assistant_message)
                if response.content:
                    print(f"💬 助手回复: {response.content}")
                break
        
        return messages
    
    # 5. 处理第一轮对话
    print("💬 第一轮对话：存储信息")
    messages = process_conversation(messages)
    
    # 6. 添加新的用户消息进行测试
    print("\n" + "=" * 50)
    print("💬 第二轮对话：检索信息")
    
    messages.append({
        "role": "user",
        "content": "Alice的职业是什么？她有什么爱好？"
    })
    
    messages = process_conversation(messages)
    
    # 7. 演示更新功能
    print("\n" + "=" * 50)
    print("💬 第三轮对话：更新信息")
    
    messages.append({
        "role": "user", 
        "content": "Alice现在26岁了，请更新她的年龄信息。"
    })
    
    messages = process_conversation(messages)
    
    print("\n🎉 示例完成！")
    print("\n📋 总结:")
    print("✅ 使用OpenAI官方function calling格式")
    print("✅ 支持多轮函数调用")
    print("✅ 正确处理工具调用和结果")
    print("✅ 维护完整的对话历史")
    print("✅ 符合OpenAI最佳实践")

if __name__ == "__main__":
    main() 