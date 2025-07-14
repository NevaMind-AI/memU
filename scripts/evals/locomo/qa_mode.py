#!/usr/bin/env python3
"""
Quick QA Mode for Enhanced Memory Agent

This script provides a quick way to start QA mode with existing memory files.
"""

import os
import sys
from pathlib import Path

import dotenv
dotenv.load_dotenv()

# 确保标准输出unbuffered
if not hasattr(sys, '_stdout_line_buffering_set'):
    sys.stdout.reconfigure(line_buffering=True)
    sys._stdout_line_buffering_set = True

from enhanced_memory_agent import EnhancedMemoryAgent
from personalab.utils import setup_logging

# 设置带有flush的logger
logger = setup_logging(__name__, enable_flush=True)


def main():
    """启动QA模式"""
    print("🧠 Enhanced Memory Agent - Quick QA Mode", flush=True)
    print("=" * 50, flush=True)
    
    # 配置参数
    config = {
        'azure_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'chat_deployment': os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4.1-mini'),
        'use_entra_id': os.getenv('USE_ENTRA_ID', 'false').lower() == 'true',
        'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01'),
        'memory_dir': 'memory'
    }
    
    # 创建agent
    try:
        agent = EnhancedMemoryAgent(**config)
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}", flush=True)
        return
    
    # 检查memory文件
    available_characters = agent.list_available_characters()
    if not available_characters:
        print("❌ No memory files found in the memory directory.", flush=True)
        print("💡 Please run the enhanced_memory_test.py first to process some sessions.", flush=True)
        return
    
    # 直接启动QA模式
    agent.start_qa_mode(available_characters)


if __name__ == "__main__":
    main() 