#!/usr/bin/env python3
"""
MemU + OpenClaw 快速集成脚本
"""

import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path

print("开始 MemU + OpenClaw 快速集成...")

# 添加 src 目录到路径
src_path = Path("C:/Users/16663/Desktop/openclaw/memU/src")
sys.path.insert(0, str(src_path))

print("路径配置完成")

# 检查桥接服务是否运行
import requests
try:
    response = requests.get("http://localhost:5000/v1/chat/completions", 
                           headers={"Content-Type": "application/json"},
                           json={"model": "test", "messages": [{"role": "user", "content": "test"}]}, 
                           timeout=5)
    print("桥接服务正在运行")
except requests.exceptions.RequestException:
    print("桥接服务未运行，请先启动 openclaw_bridge.py")
    sys.exit(1)

print("\nMemU + OpenClaw 集成成功启动！")
print("桥接服务运行在 http://localhost:5000/v1")
print("准备就绪，可以开始使用主动记忆功能")
print("\n下一步操作：")
print("- 运行 'python proactive_loop.py' 开始主动记忆监控")
print("- 运行 'python import_legacy.py' 导入遗留记忆")
print("- 运行 'python manager.py' 进行系统管理")