#!/usr/bin/env python3
"""
PersonaLab命令行工具

提供快速测试和演示功能
"""

import argparse
import os


def check_environment():
    """检查环境配置"""
    print("🔍 检查PersonaLab环境...")

    # 检查OpenAI API Key
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OPENAI_API_KEY 已设置")
    else:
        print("❌ OPENAI_API_KEY 未设置")
        print("   请运行: export OPENAI_API_KEY='your-api-key'")

    # 检查导入
    try:
        from personalab import Persona

        print("✅ PersonaLab 导入成功")
    except ImportError as e:
        print(f"❌ PersonaLab 导入失败: {e}")
        return False

    # 检查OpenAI
    try:
        from openai import OpenAI

        print("✅ OpenAI 库可用")
    except ImportError:
        print("❌ OpenAI 库未安装")
        print("   请运行: pip install openai")
        return False

    return True


def quick_test():
    """快速测试PersonaLab功能"""
    print("🚀 PersonaLab 快速测试")
    print("-" * 40)

    if not check_environment():
        return

    try:
        from personalab import Persona

        print("\n📱 初始化PersonaLab...")
        persona = Persona()

        # 测试对话
        test_messages = [
            "你好，我叫小明，我在学习Python编程",
            "你记得我的名字吗？",
            "我之前说在学什么？",
        ]

        print("\n💬 开始测试对话...")
        for i, message in enumerate(test_messages, 1):
            print(f"\n第{i}轮:")
            print(f"👤 用户: {message}")

            try:
                response = persona.chat(message, user_id="test_user")
                print(f"🤖 AI: {response}")
            except Exception as e:
                print(f"❌ 错误: {e}")
                if "api" in str(e).lower():
                    print("   请检查OPENAI_API_KEY是否正确")
                break

        print("\n✅ 测试完成！PersonaLab工作正常")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


def interactive_chat():
    """交互式聊天模式"""
    print("🗣️ PersonaLab 交互式聊天")
    print("输入 'exit' 退出")
    print("-" * 40)

    if not check_environment():
        return

    try:
        from personalab import Persona

        persona = Persona()

        while True:
            user_input = input("\n👤 你: ").strip()
            if user_input.lower() in ["exit", "quit", "退出"]:
                print("👋 再见！")
                break

            if not user_input:
                continue

            try:
                response = persona.chat(user_input, user_id="interactive_user")
                print(f"🤖 AI: {response}")
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PersonaLab 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  personalab check          # 检查环境配置
  personalab test           # 快速功能测试
  personalab chat           # 交互式聊天
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 检查命令
    subparsers.add_parser("check", help="检查环境配置")

    # 测试命令
    subparsers.add_parser("test", help="快速功能测试")

    # 聊天命令
    subparsers.add_parser("chat", help="交互式聊天模式")

    args = parser.parse_args()

    if args.command == "check":
        check_environment()
    elif args.command == "test":
        quick_test()
    elif args.command == "chat":
        interactive_chat()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
