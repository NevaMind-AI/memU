# 2. 获取或创建代理内存
print("2. 创建AI代理内存...")
agent_id = "learning_assistant"
user_id = "student_001"  # 添加用户ID
memory = memory_manager.get_memory_by_agent(agent_id, user_id)

print(f"✅ 代理内存创建成功")
print(f"   代理ID: {agent_id}")
print(f"   用户ID: {user_id}")
print(f"   内存ID: {memory.memory_id}")
print() 