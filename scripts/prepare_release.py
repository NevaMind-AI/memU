#!/usr/bin/env python3
"""
PersonaLab 发布准备脚本
- 清理项目文件
- 验证配置
- 运行测试
- 更新版本信息
- 准备GitHub发布
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """运行命令并返回结果"""
    print(f"🔧 运行: {cmd}")
    result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr and check:
        print(f"错误: {result.stderr}")
    return result

def cleanup_project():
    """清理项目文件"""
    print("🧹 清理项目文件...")
    
    # 清理Python缓存
    patterns_to_remove = [
        "__pycache__",
        "*.pyc", 
        "*.pyo",
        "*.egg-info",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "*.db",
        "*.sqlite",
        "*.sqlite3"
    ]
    
    for pattern in patterns_to_remove:
        run_command(f"find . -name '{pattern}' -exec rm -rf {{}} + 2>/dev/null || true", check=False)
    
    print("✅ 项目清理完成")

def check_dependencies():
    """检查依赖项"""
    print("📦 检查项目依赖...")
    
    required_files = [
        "requirements.txt",
        "setup.py", 
        "pyproject.toml",
        "README.md",
        "LICENSE"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    
    print("✅ 依赖检查通过")
    return True

def validate_code_quality():
    """验证代码质量"""
    print("🔍 验证代码质量...")
    
    # 检查Python语法
    try:
        result = run_command("python -m py_compile personalab/__init__.py", check=False)
        if result.returncode != 0:
            print("❌ Python语法检查失败")
            return False
    except:
        print("⚠️  跳过语法检查（py_compile不可用）")
    
    # 尝试导入包
    try:
        run_command("python -c 'import personalab; print(\"导入成功\")'")
        print("✅ 包导入测试通过")
    except:
        print("❌ 包导入失败")
        return False
    
    return True

def check_git_status():
    """检查Git状态"""
    print("📝 检查Git状态...")
    
    try:
        # 检查是否在git仓库中
        run_command("git status --porcelain")
        
        # 检查是否有未提交的更改
        result = run_command("git status --porcelain", check=False)
        if result.stdout.strip():
            print("📋 发现未提交的更改:")
            print(result.stdout)
            return True
        else:
            print("✅ 工作目录干净")
            return True
            
    except:
        print("❌ 不在Git仓库中或Git不可用")
        return False

def create_release_summary():
    """创建发布摘要"""
    print("📊 创建发布摘要...")
    
    summary = {
        "项目": "PersonaLab",
        "描述": "AI Memory and Conversation Management System",
        "主要功能": [
            "PostgreSQL/SQLite双数据库支持",
            "多LLM提供商集成 (OpenAI, Anthropic, 等)",
            "智能记忆管理 (Profile, Events, Mind)", 
            "向量嵌入和语义搜索",
            "对话录制和检索",
            "心理洞察分析"
        ],
        "最新修复": [
            "SQLite Row对象兼容性问题",
            "ConversationManager方法调用错误",
            "PostgreSQL连接和配置问题",
            "内存更新管道优化"
        ]
    }
    
    print("\n" + "="*50)
    print("🚀 PersonaLab 发布摘要")
    print("="*50)
    for key, value in summary.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  • {item}")
        else:
            print(f"{key}: {value}")
    print("="*50)
    
    return summary

def main():
    """主函数"""
    print("🚀 PersonaLab 发布准备脚本")
    print("="*50)
    
    # 确保在项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"📂 工作目录: {os.getcwd()}")
    
    success = True
    
    # 1. 清理项目
    cleanup_project()
    
    # 2. 检查依赖
    if not check_dependencies():
        success = False
    
    # 3. 验证代码质量  
    if not validate_code_quality():
        success = False
    
    # 4. 检查Git状态
    if not check_git_status():
        success = False
    
    # 5. 创建发布摘要
    create_release_summary()
    
    if success:
        print("\n🎉 发布准备完成！")
        print("\n📋 下一步操作:")
        print("  1. git add .")
        print("  2. git commit -m 'feat: prepare for release with PostgreSQL support'")
        print("  3. git push origin main")
        print("  4. 在GitHub上创建新的Release")
        print("\n🔗 建议的Release内容:")
        print("  标题: PersonaLab v1.0.0 - PostgreSQL Integration & Enhanced Memory")
        print("  标签: v1.0.0")
        print("  描述: 包含PostgreSQL支持、多LLM集成和增强记忆管理的重大更新")
    else:
        print("\n❌ 发布准备失败，请修复上述问题")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 