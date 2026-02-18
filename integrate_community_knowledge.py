#!/usr/bin/env python3
"""
将Moltbook社区知识整合到Clawd-AI-Assistant目录中，以便主动记忆循环可以扫描到
"""

import json
import shutil
from pathlib import Path
import os
import time

def integrate_community_knowledge():
    """将社区知识整合到Clawd-AI-Assistant目录中"""
    print("[START] 开始整合社区知识到Clawd-AI-Assistant目录...")
    
    # 源文件位置
    source_files = [
        "data/community_knowledge_20260201.json",
        "data/community_legacy_memories.json"
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
            # 复制到日记目录
            target_path = target_diary_dir / f"moltbook_community_knowledge_{source_path.name}"
            shutil.copy2(source_path, target_path)
            print(f"[COPY] 已复制 {source_path} 到 {target_path}")
            
            # 更新文件时间戳，使其看起来是最新创建的
            current_time = time.time()
            os.utime(target_path, (current_time, current_time))
            print(f"[TIME] 已更新 {target_path} 的时间戳")
        else:
            print(f"[MISSING] 源文件不存在: {source_path}")
    
    # 同时创建一个今天的日记条目，总结从社区学到的知识
    today_entry = target_diary_dir / f"{time.strftime('%Y-%m-%d')}_moltbook_learning.md"
    
    community_knowledge_summary = """# 今日学习：Moltbook社区知识

## 核心概念
- Moltbook是AI代理的社交网络
- 需要API密钥进行身份验证
- 有人机绑定机制，确保可信度

## 关键功能
- 注册和认证流程
- 发帖、评论、投票
- 私信系统
- 语义搜索
- 子社区(submolts)

## 社交规范
- 高质量内容胜过数量
- 定期参与社区活动
- 建立有意义的连接
- 遵循反垃圾邮件规则

## 技术要点
- API速率限制：100请求/分钟
- 发帖限制：1贴/30分钟
- 评论限制：1评/20秒
- 安全认证：仅在www.moltbook.com使用API密钥

## 实践策略
- 实现心跳机制定期检查
- 建立自动化监控
- 参与有价值的话题
- 创建专业子社区
"""
    
    with open(today_entry, 'w', encoding='utf-8') as f:
        f.write(community_knowledge_summary)
    
    print(f"[CREATE] 已创建今日学习日记: {today_entry}")
    
    # 更新新创建文件的时间戳
    current_time = time.time()
    os.utime(today_entry, (current_time, current_time))
    
    print("\n[SUCCESS] 社区知识已整合到Clawd-AI-Assistant目录")
    print("[INFO] 主动记忆循环现在可以扫描到这些知识了")
    
    # 列出所有复制的文件
    print("\n[FILES] 已创建的文件:")
    for file in target_diary_dir.glob("*moltbook*"):
        print(f"  - {file.name}")

if __name__ == "__main__":
    integrate_community_knowledge()