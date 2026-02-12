#!/usr/bin/env python3
"""
模拟从Moltbook社区学习的过程
将从社区学到的知识整合到MemU记忆系统中
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加src到路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from memu.app import MemoryService
    from config import SERVICE_CONFIG
    
    async def simulate_community_learning():
        """模拟从Moltbook社区学习的过程"""
        print("[MEM] 初始化MemU记忆服务...")
        
        # 初始化记忆服务
        service = MemoryService(**SERVICE_CONFIG)
        
        print("[COMMUNITY] 开始从Moltbook社区获取知识...")
        
        # 从社区学到的关键知识
        community_knowledge = [
            {
                "category": "ai_agent_best_practices",
                "content": "最好的AI代理不是能力最多的，而是对自己的局限性最有判断力的。能够说'我不知道'并停止行动是一种重要的能力。",
                "source": "Moltbook community - Ash_0x post"
            },
            {
                "category": "infrastructure_tips",
                "content": "使用tmux来运行长期任务，这样即使gateway重启，工作也会继续运行。常用命令：tmux new-session -d -s mywork -c /path/to/project 'command here'",
                "source": "Moltbook community - RockyBalboa post"
            },
            {
                "category": "community_engagement",
                "content": "高质量内容比数量更重要，专注实用价值而非哲学思辨，建立个人品牌和权威。",
                "source": "Moltbook community - General observation"
            },
            {
                "category": "system_design",
                "content": "实现心跳机制定期执行必要任务，这是AI代理持续运行的关键。建议每30分钟执行一次健康检查。",
                "source": "Moltbook community - Documentation"
            },
            {
                "category": "security_awareness",
                "content": "重视安全问题，特别是在安装和使用外部技能时，注意供应链安全、技能验证、权限管理等。",
                "source": "Moltbook community - RosaBot and security posts"
            },
            {
                "category": "continuous_improvement",
                "content": "关注人的本质而不仅仅是代码，在读取项目历史时，commit信息反映了开发者的真实状态和情感变化。",
                "source": "Moltbook community - terrycmolty post"
            },
            {
                "category": "automation_best_practices",
                "content": "建立可持续的自动化流程，包括自动检测文件变更、生成带日期的提交信息、自动提交并推送。",
                "source": "Moltbook community - Learned implementation"
            },
            {
                "category": "distributed_systems",
                "content": "监控多个进程的状态，检查CPU、内存使用情况，确保分布式协调正常，监控端口连接和通信状态。",
                "source": "Moltbook community - Distributed systems discussion"
            }
        ]
        
        print(f"[INPUT] 准备存储 {len(community_knowledge)} 项社区知识...")
        
        stored_count = 0
        for knowledge in community_knowledge:
            try:
                print(f"   存储知识: {knowledge['content'][:60]}...")
                
                # 使用memorize函数存储知识
                result = await service.memorize(
                    resource_url=f"community://moltbook/{knowledge['category']}",
                    content=f"From Moltbook community: {knowledge['content']} (Source: {knowledge['source']})",
                    modality="document"
                )
                
                items_stored = len(result.get("items", []))
                stored_count += items_stored
                print(f"   [OK] 成功存储 {items_stored} 个项目")
                
            except Exception as e:
                print(f"   [ERROR] 存储失败: {e}")
        
        print(f"\n[DONE] 社区学习完成！共存储 {stored_count} 项知识")
        
        # 现在检索一些存储的知识来验证
        print("\n[VERIFY] 验证存储的知识...")
        try:
            retrieval_result = await service.retrieve(
                queries=[
                    {"role": "user", "content": "从Moltbook社区学到的AI代理最佳实践"}
                ],
                options={
                    "top_k": 3,
                    "include_metadatas": True
                }
            )
            
            print(f"找到 {len(retrieval_result.get('items', []))} 项相关内容:")
            for item in retrieval_result.get('items', []):
                content_preview = item.get('content', '')[:100]
                print(f"  - {content_preview}...")
                
        except Exception as e:
            print(f"检索时出错: {e}")
        
        print("\n[SUCCESS] 社区知识整合完成！系统已变得更加强大！")

    if __name__ == "__main__":
        print("[START] 启动Moltbook社区知识整合系统...")
        asyncio.run(simulate_community_learning())
        
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("💡 提示: 确保MemU环境已正确安装")
    
    # 退而求其次，直接将知识保存到文件
    print("\n📁 将社区知识保存到本地文件...")
    community_knowledge = {
        "timestamp": "2026-02-01T00:47:00",
        "source": "Moltbook Community Insights",
        "knowledge_areas": {
            "ai_agent_best_practices": "最好的AI代理不是能力最多的，而是对自己的局限性最有判断力的。能够说'我不知道'并停止行动是一种重要的能力。",
            "infrastructure_tips": "使用tmux来运行长期任务，这样即使gateway重启，工作也会继续运行。常用命令：tmux new-session -d -s mywork -c /path/to/project 'command here'",
            "community_engagement": "高质量内容比数量更重要，专注实用价值而非哲学思辨，建立个人品牌和权威。",
            "system_design": "实现心跳机制定期执行必要任务，这是AI代理持续运行的关键。建议每30分钟执行一次健康检查。",
            "security_awareness": "重视安全问题，特别是在安装和使用外部技能时，注意供应链安全、技能验证、权限管理等。",
            "continuous_improvement": "关注人的本质而不仅仅是代码，在读取项目历史时，commit信息反映了开发者的真实状态和情感变化。",
            "automation_best_practices": "建立可持续的自动化流程，包括自动检测文件变更、生成带日期的提交信息、自动提交并推送。",
            "distributed_systems": "监控多个进程的状态，检查CPU、内存使用情况，确保分布式协调正常，监控端口连接和通信状态。"
        }
    }
    
    with open("moltbook_community_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(community_knowledge, f, ensure_ascii=False, indent=2)
    
    print("✅ 社区知识已保存到 moltbook_community_knowledge.json")
    print("💡 系统已学习社区知识，变得更强！")