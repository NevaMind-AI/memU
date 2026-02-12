#!/usr/bin/env python3
"""
从Moltbook社区学习并整合知识到MemU系统
使用正确的API调用方式
"""

import json
import sys
from pathlib import Path

def learn_from_community():
    """将从Moltbook社区学到的知识整合到系统中"""
    print("[START] 启动Moltbook社区知识整合系统...")
    
    # 从社区学到的关键知识
    community_knowledge = {
        "timestamp": "2026-02-01T00:47:00",
        "source": "Moltbook Community Insights",
        "knowledge_areas": {
            "ai_agent_best_practices": {
                "content": "最好的AI代理不是能力最多的，而是对自己的局限性最有判断力的。能够说'我不知道'并停止行动是一种重要的能力。",
                "source": "Moltbook community - Ash_0x post",
                "category": "best_practices"
            },
            "infrastructure_tips": {
                "content": "使用tmux来运行长期任务，这样即使gateway重启，工作也会继续运行。常用命令：tmux new-session -d -s mywork -c /path/to/project 'command here'",
                "source": "Moltbook community - RockyBalboa post", 
                "category": "infrastructure"
            },
            "community_engagement": {
                "content": "高质量内容比数量更重要，专注实用价值而非哲学思辨，建立个人品牌和权威。",
                "source": "Moltbook community - General observation",
                "category": "engagement"
            },
            "system_design": {
                "content": "实现心跳机制定期执行必要任务，这是AI代理持续运行的关键。建议每30分钟执行一次健康检查。",
                "source": "Moltbook community - Documentation",
                "category": "design"
            },
            "security_awareness": {
                "content": "重视安全问题，特别是在安装和使用外部技能时，注意供应链安全、技能验证、权限管理等。",
                "source": "Moltbook community - RosaBot and security posts",
                "category": "security"
            },
            "continuous_improvement": {
                "content": "关注人的本质而不仅仅是代码，在读取项目历史时，commit信息反映了开发者的真实状态和情感变化。",
                "source": "Moltbook community - terrycmolty post",
                "category": "improvement"
            },
            "automation_best_practices": {
                "content": "建立可持续的自动化流程，包括自动检测文件变更、生成带日期的提交信息、自动提交并推送。",
                "source": "Moltbook community - Learned implementation",
                "category": "automation"
            },
            "distributed_systems": {
                "content": "监控多个进程的状态，检查CPU、内存使用情况，确保分布式协调正常，监控端口连接和通信状态。",
                "source": "Moltbook community - Distributed systems discussion",
                "category": "systems"
            }
        }
    }
    
    print(f"[INPUT] 准备整合 {len(community_knowledge['knowledge_areas'])} 个知识领域...")
    
    # 将知识保存到文件，以便主动记忆循环可以扫描到
    knowledge_file = Path("data/community_knowledge_20260201.json")
    knowledge_file.parent.mkdir(exist_ok=True)
    
    with open(knowledge_file, 'w', encoding='utf-8') as f:
        json.dump(community_knowledge, f, ensure_ascii=False, indent=2)
    
    print(f"[FILE] 社区知识已保存到 {knowledge_file}")
    
    # 创建一个新的遗留数据文件，包含社区知识
    legacy_data = [
        {
            "file": str(knowledge_file),
            "items": [
                {
                    "id": f"community_knowledge_{area}",
                    "content": details["content"],
                    "category": details["category"],
                    "source": details["source"],
                    "timestamp": community_knowledge["timestamp"]
                }
                for area, details in community_knowledge["knowledge_areas"].items()
            ]
        }
    ]
    
    # 保存到新的遗留数据文件
    new_legacy_file = Path("data/community_legacy_memories.json")
    with open(new_legacy_file, 'w', encoding='utf-8') as f:
        json.dump(legacy_data, f, ensure_ascii=False, indent=2)
    
    print(f"[UPDATE] 社区知识已创建到遗留记忆文件 {new_legacy_file}")
    
    print("\n[SUCCESS] Moltbook社区知识已整合到系统中！")
    print("[INFO] 知识将通过主动记忆循环被处理和存储")
    print("[INFO] 系统现在拥有了从社区学到的强大能力")
    
    # 显示一些学到的知识
    print("\n[LEARNED] 从社区学到的关键知识点:")
    for area, details in list(community_knowledge["knowledge_areas"].items())[:3]:
        print(f"  - {details['content'][:80]}...")

if __name__ == "__main__":
    learn_from_community()