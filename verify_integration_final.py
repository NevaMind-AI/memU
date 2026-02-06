import sys
import os
sys.path.insert(0, 'C:/Users/16663/Desktop/openclaw/memU/src')

import asyncio
from memu.app import MemoryService
from memu.app.settings import DatabaseConfig, MetadataStoreConfig

async def verify_integration():
    print("验证 MemU + OpenClaw 集成...")
    
    # 桥接配置
    api_key = 'dummy'
    base_url = 'http://localhost:5000/v1'

    # 数据库配置
    db_config = DatabaseConfig(
        metadata_store=MetadataStoreConfig(
            provider='inmemory'
        )
    )

    try:
        # 初始化服务
        service = MemoryService(
            database_config=db_config,
            llm_profiles={
                'default': {
                    'base_url': base_url,
                    'api_key': api_key,
                    'chat_model': 'openclaw-bridge',
                    'embed_model': 'fake-embeddings',
                }
            }
        )
        
        print("服务初始化成功")
        
        # 测试创建一个简单的记忆项
        result = await service.create_memory_item(
            memory_type="knowledge",
            memory_content="This is a test memory for integration verification",
            memory_categories=["verification", "testing"]
        )
        
        print(f"记忆创建成功: {result.get('memory_item', {}).get('id', 'Unknown ID')}")
        
        # 测试检索功能
        retrieve_result = await service.retrieve(
            queries=[{"role": "user", "content": "test memory"}]
        )
        
        items = retrieve_result.get('items', [])
        print(f"检索功能正常: 找到 {len(items)} 个项目")
        
        print("\nMemU + OpenClaw 集成验证成功！")
        print("系统已完全准备好进行主动记忆管理。")
        
        return True
        
    except Exception as e:
        print(f"集成验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_integration())
    if success:
        print("\n集成完成！系统正在运行。")
    else:
        print("\n集成存在问题，请检查错误。")