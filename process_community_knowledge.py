#!/usr/bin/env python3
"""
处理社区知识并将其存储到MemU系统中
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加src到路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

async def process_community_knowledge():
    try:
        from memu.app import MemoryService
        from config import SERVICE_CONFIG
        
        print('[PROCESS] 开始处理社区知识...')
        
        # 初始化记忆服务
        service = MemoryService(**SERVICE_CONFIG)
        
        # 读取社区知识
        with open('data/community_knowledge_20260201.json', 'r', encoding='utf-8') as f:
            community_data = json.load(f)
        
        print(f'[DATA] 加载了 {len(community_data["knowledge_areas"])} 个知识领域')
        
        # 将每个知识领域作为一个独立的资源存储
        stored_count = 0
        for area, details in community_data['knowledge_areas'].items():
            try:
                print(f'  [STORE] 存储 {area}...')
                
                result = await service.memorize(
                    resource_url=f'community://moltbook/{area}',
                    content=f'{details["content"]}\n来源: {details["source"]}',
                    modality='document'
                )
                
                items_created = len(result.get('items', []))
                stored_count += items_created
                print(f'    [OK] 创建了 {items_created} 个记忆项目')
                
            except Exception as e:
                print(f'    [ERROR] 存储失败: {e}')
        
        print(f'\n[COMPLETE] 总共处理了 {stored_count} 个社区知识项目')
        print('[SUCCESS] 社区知识已成功整合到记忆系统!')
        
    except ImportError as e:
        print(f'[ERROR] 无法导入MemU模块: {e}')
        print('[INFO] 直接将社区知识保存到记忆文件中...')
        
        # 如果无法导入MemU，直接将知识添加到遗留记忆文件
        legacy_file = Path("data/legacy_memory_consolidated.json")
        
        # 读取现有内容或创建新内容
        if legacy_file.exists():
            with open(legacy_file, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
        else:
            legacy_data = []
        
        # 添加社区知识到遗留数据
        from datetime import datetime
        community_knowledge = {
            "file": "moltbook_community_integration",
            "items": [
                {
                    "id": f"moltbook_knowledge_{area}",
                    "content": details["content"],
                    "category": details["category"],
                    "source": details["source"],
                    "timestamp": datetime.now().isoformat()
                }
                for area, details in community_data["knowledge_areas"].items()
            ]
        }
        
        legacy_data.append(community_knowledge)
        
        # 保存更新后的遗留数据
        with open(legacy_file, 'w', encoding='utf-8') as f:
            json.dump(legacy_data, f, ensure_ascii=False, indent=2)
        
        print(f'[FILE] 社区知识已添加到 {legacy_file}')

if __name__ == "__main__":
    # 尝试运行异步函数
    try:
        asyncio.run(process_community_knowledge())
    except RuntimeError:
        # 如果事件循环已运行，使用同步方法
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, process_community_knowledge())
            future.result()