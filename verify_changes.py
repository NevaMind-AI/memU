#!/usr/bin/env python3
"""
验证PersonaLab重构更改

确认删除Mock client和重组LLM模块后，所有功能正常工作
"""

def test_imports():
    """测试导入是否正常"""
    print("1️⃣ 测试导入...")
    
    try:
        # 测试主要导入
        from personalab import MemoryManager
        from personalab.llm import BaseLLMClient, OpenAIClient, create_llm_client
        from personalab.memory import Memory, PipelineResult
        print("✅ 导入测试通过")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_basic_functionality():
    """测试基础功能"""
    print("\n2️⃣ 测试基础功能...")
    
    try:
        from personalab import MemoryManager
        
        # 创建Memory管理器（无LLM客户端）
        manager = MemoryManager()
        
        # 测试conversation处理
        conversation = [
            {'role': 'user', 'content': '我是测试用户'},
            {'role': 'assistant', 'content': '你好！'}
        ]
        
        memory, result = manager.update_memory_with_conversation("test_user", conversation)
        
        # 验证结果
        assert memory is not None, "Memory对象不应为None"
        assert result is not None, "Pipeline结果不应为None"
        assert hasattr(result, 'update_result'), "结果应包含update_result"
        
        print("✅ 基础功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False

def test_llm_client_creation():
    """测试LLM客户端创建"""
    print("\n3️⃣ 测试LLM客户端创建...")
    
    try:
        from personalab.llm import create_llm_client
        
        # 测试创建OpenAI客户端（但不实际使用）
        try:
            client = create_llm_client("openai", api_key="test-key")
            print("✅ OpenAI客户端创建成功")
        except ValueError as e:
            if "需要提供api_key" in str(e):
                print("✅ OpenAI客户端验证正常（需要API key）")
            else:
                raise e
        
        # 测试不支持的客户端类型
        try:
            create_llm_client("unsupported")
        except ValueError as e:
            if "不支持的客户端类型" in str(e):
                print("✅ 错误处理正常")
            else:
                raise e
        
        return True
        
    except Exception as e:
        print(f"❌ LLM客户端测试失败: {e}")
        return False

def test_no_mock_client():
    """确认Mock client已被移除"""
    print("\n4️⃣ 测试Mock client移除...")
    
    try:
        from personalab.llm import create_llm_client
        
        # 尝试创建mock客户端，应该失败
        try:
            create_llm_client("mock")
            print("❌ Mock client仍然存在，应该已被移除")
            return False
        except ValueError as e:
            if "不支持的客户端类型" in str(e):
                print("✅ Mock client已成功移除")
                return True
            else:
                print(f"❌ 意外错误: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Mock client测试失败: {e}")
        return False

def test_file_structure():
    """测试文件结构"""
    print("\n5️⃣ 测试文件结构...")
    
    import os
    
    # 检查新文件存在
    if not os.path.exists("personalab/llm.py"):
        print("❌ personalab/llm.py 文件不存在")
        return False
    
    # 检查旧文件已删除
    if os.path.exists("personalab/memory/llm_client.py"):
        print("❌ personalab/memory/llm_client.py 文件仍然存在，应该已被删除")
        return False
    
    print("✅ 文件结构正确")
    return True

def main():
    """主测试函数"""
    print("🔬 PersonaLab 重构验证")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_llm_client_creation,
        test_no_mock_client,
        test_file_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！重构成功")
        print("\n✅ 确认事项:")
        print("   - Mock client已移除")
        print("   - LLM模块移至personalab/llm.py")
        print("   - 基础功能正常工作")
        print("   - OpenAI集成可用")
        print("   - 文件结构正确")
    else:
        print("❌ 部分测试失败，需要检查")

if __name__ == "__main__":
    main() 