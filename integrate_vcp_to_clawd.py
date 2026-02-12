#!/usr/bin/env python3
"""
将VCP知识整合到Clawd-AI-Assistant目录中，以便主动记忆循环可以扫描到
"""

import json
import shutil
from pathlib import Path
import os
import time

def integrate_vcp_to_clawd():
    """将VCP知识整合到Clawd-AI-Assistant目录中"""
    print("[START] 开始整合VCP知识到Clawd-AI-Assistant目录...")
    
    # 源文件位置
    source_files = [
        "data/vcp_knowledge.json",
        "data/vcp_integration_summary.md"
    ]
    
    # 目标目录
    target_diary_dir = Path(r"C:\Users\16663\Desktop\Clawd-AI-Assistant\diary")
    target_logs_dir = Path(r"C:\Users\16663\Desktop\Clawd-AI-Assistant\logs")
    
    # 确保目标目录存在
    target_diary_dir.mkdir(parents=True, exist_ok=True)
    target_logs_dir.mkdir(parents=True, exist_ok=True)
    
    # 移动文件到日记目录，这样主动记忆循环就能找到它们
    for source_file in source_files:
        source_path = Path(source_file)
        if source_path.exists():
            # 根据文件类型决定目标文件名
            if source_path.suffix == '.json':
                target_path = target_diary_dir / f"vcp_project_analysis_{source_path.name}"
            else:
                target_path = target_diary_dir / f"vcp_integration_summary_{source_path.name}"
                
            shutil.copy2(source_path, target_path)
            print(f"[COPY] 已复制 {source_path} 到 {target_path}")
            
            # 更新文件时间戳，使其看起来是最新创建的
            current_time = time.time()
            os.utime(target_path, (current_time, current_time))
            print(f"[TIME] 已更新 {target_path} 的时间戳")
        else:
            print(f"[MISSING] 源文件不存在: {source_path}")
    
    # 创建一个今天的日记条目，总结VCPToolBox项目
    today_entry = target_diary_dir / f"{time.strftime('%Y-%m-%d')}_vcp_project_summary.md"
    
    vcp_summary = """# 今日学习：VCPToolBox项目分析

## 项目概述
VCP (Variable & Command Protocol) 是新一代AI能力增强与进化中间层，具有分布式架构、记忆系统和插件生态。

## 核心组件
- **主服务器 (server.js)**: 基于Express.js的API网关，提供标准化OpenAI API接口，集成WebSocket服务器进行实时通信
- **插件系统 (Plugin.js)**: 插件管理系统，支持多种插件类型，提供热加载和依赖注入机制
- **知识库 (KnowledgeBaseManager.js)**: 知识库管理系统，基于SQLite和Rust的高性能向量数据库
- **WebSocket服务器 (WebSocketServer.js)**: 支持多种客户端类型和跨服务器通信

## 架构特点
- **分布式**: 星型网络拓扑：主服务器与多个分布式节点
- **插件生态**: 300+官方插件，支持六种插件协议
- **记忆系统**: TagMemo浪潮算法，基于语义引力和向量重塑的RAG优化
- **安全**: 集成验证码和权限控制系统

## 技术特性
- 高性能：使用Rust重写底层数据抽象层
- 模型无关：兼容各种AI模型API
- 动态扩展：支持插件热加载和动态工具注入
- 企业级：支持分布式部署和多租户隔离

## 与OpenClaw集成点
- 可通过API与OpenClaw集成
- 插件系统可扩展OpenClaw功能
- 记忆系统可与memU协同工作
- WebSocket通信可桥接两个系统
"""
    
    with open(today_entry, 'w', encoding='utf-8') as f:
        f.write(vcp_summary)
    
    print(f"[CREATE] 已创建VCP项目总结日记: {today_entry}")
    
    # 更新新创建文件的时间戳
    current_time = time.time()
    os.utime(today_entry, (current_time, current_time))
    
    print("\n[SUCCESS] VCP知识已整合到Clawd-AI-Assistant目录")
    print("[INFO] 主动记忆循环现在可以扫描到这些知识了")
    
    # 列出所有复制的文件
    print("\n[FILES] 已创建的文件:")
    for file in target_diary_dir.glob("*vcp*"):
        print(f"  - {file.name}")

if __name__ == "__main__":
    integrate_vcp_to_clawd()