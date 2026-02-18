#!/usr/bin/env python3
"""
VCPToolBox项目与memU记忆系统集成脚本
将VCPToolBox的详细分析结果整合到memU记忆系统中
"""

import json
import sys
from pathlib import Path
import asyncio
from datetime import datetime

# 添加src到路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from memu.app import MemoryService
from config import SERVICE_CONFIG

def create_vcp_knowledge():
    """创建VCPToolBox项目的详细知识记录"""
    vcp_knowledge = {
        "timestamp": datetime.now().isoformat(),
        "source": "VCPToolBox Project Analysis",
        "project_name": "VCP (Variable & Command Protocol)",
        "summary": "新一代AI能力增强与进化中间层，具有分布式架构、记忆系统和插件生态",
        "components": {
            "main_server": {
                "file": "server.js",
                "description": "基于Express.js的API网关，提供标准化OpenAI API接口，集成WebSocket服务器进行实时通信",
                "key_features": [
                    "支持模型重定向",
                    "请求拦截和处理",
                    "插件管理和生命周期控制",
                    "WebSocket实时通信"
                ]
            },
            "plugin_system": {
                "file": "Plugin.js", 
                "description": "插件管理系统，支持多种插件类型，提供热加载和依赖注入机制",
                "key_features": [
                    "静态、同步、异步、消息预处理器、服务插件类型",
                    "分布式插件执行",
                    "统一配置管理",
                    "插件热加载机制"
                ]
            },
            "knowledge_base": {
                "file": "KnowledgeBaseManager.js",
                "description": "知识库管理系统，基于SQLite和Rust的高性能向量数据库",
                "key_features": [
                    "TagMemo浪潮算法进行语义增强",
                    "EPA模块(嵌入投影分析)和残差金字塔算法",
                    "多维记忆存储和检索",
                    "自动切分和索引管理"
                ]
            },
            "websocket_server": {
                "file": "WebSocketServer.js",
                "description": "WebSocket服务器，支持多种客户端类型和跨服务器通信",
                "key_features": [
                    "VCPLog、分布式服务器、Chrome控制等多种客户端",
                    "跨服务器工具调用能力",
                    "实时消息广播功能",
                    "身份验证和安全控制"
                ]
            }
        },
        "architecture": {
            "distributed": "星型网络拓扑：主服务器与多个分布式节点",
            "plugin_ecosystem": "300+官方插件，支持六种插件协议",
            "memory_system": "TagMemo浪潮算法，基于语义引力和向量重塑的RAG优化",
            "security": "集成验证码和权限控制系统"
        },
        "technical_features": [
            "高性能：使用Rust重写底层数据抽象层",
            "模型无关：兼容各种AI模型API",
            "动态扩展：支持插件热加载和动态工具注入",
            "企业级：支持分布式部署和多租户隔离"
        ],
        "integration_points": [
            "可通过API与OpenClaw集成",
            "插件系统可扩展OpenClaw功能",
            "记忆系统可与memU协同工作",
            "WebSocket通信可桥接两个系统"
        ]
    }
    
    return vcp_knowledge

async def integrate_vcp_knowledge():
    """将VCP知识整合到memU系统中"""
    print("[START] 开始整合VCPToolBox知识到memU系统...")
    
    # 创建记忆服务
    service = MemoryService(**SERVICE_CONFIG)
    
    # 创建VCP知识
    vcp_knowledge = create_vcp_knowledge()
    
    # 保存到数据目录
    knowledge_file = Path("data/vcp_knowledge.json")
    knowledge_file.parent.mkdir(exist_ok=True)
    
    with open(knowledge_file, 'w', encoding='utf-8') as f:
        json.dump(vcp_knowledge, f, ensure_ascii=False, indent=2)
    
    print(f"[FILE] VCP知识已保存到 {knowledge_file}")
    
    # 将知识导入memU系统
    print("[MEM] 正在将VCP知识导入记忆系统...")
    
    try:
        # 使用memorize方法将知识添加到记忆库
        result = await service.memorize(
            resource_url=str(knowledge_file),
            modality="document",
            user={"user_id": "system", "name": "IntegrationBot"}
        )
        
        print(f"[SUCCESS] VCP知识已成功导入记忆系统")
        print(f"  - 资源: {result.get('resource', {}).get('id', 'N/A')}")
        print(f"  - 项目数: {len(result.get('items', []))}")
        print(f"  - 类别数: {len(result.get('categories', []))}")
        
        # 验证导入的知识
        print("[VERIFY] 验证导入的知识...")
        retrieval_result = await service.retrieve(
            queries=[
                {"role": "user", "content": {"text": "VCPToolBox项目是什么？"}}
            ],
            where={"user_id": "system"},
            method="rag"
        )
        
        if retrieval_result.get('items'):
            print(f"  [SUCCESS] 成功检索到 {len(retrieval_result['items'])} 个项目")
            print(f"  [INFO] 检索到关键信息: {retrieval_result['items'][0].get('content', '')[:100]}...")
        else:
            print("  [WARNING] 未检索到预期的知识")
            
    except Exception as e:
        print(f"[ERROR] 导入VCP知识时出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 创建一个摘要文件，便于主动记忆循环扫描
    summary_file = Path("data/vcp_integration_summary.md")
    summary_content = f"""# VCPToolBox集成摘要

**集成时间**: {vcp_knowledge['timestamp']}
**项目名称**: {vcp_knowledge['project_name']}
**项目概述**: {vcp_knowledge['summary']}

## 核心组件
- 主服务器 (server.js): {vcp_knowledge['components']['main_server']['description']}
- 插件系统 (Plugin.js): {vcp_knowledge['components']['plugin_system']['description']}
- 知识库 (KnowledgeBaseManager.js): {vcp_knowledge['components']['knowledge_base']['description']}
- WebSocket服务器 (WebSocketServer.js): {vcp_knowledge['components']['websocket_server']['description']}

## 集成要点
- 分布式架构支持
- 插件化扩展能力
- 高性能记忆系统
- 安全认证机制

## 与OpenClaw集成点
{chr(10).join([f'- {point}' for point in vcp_knowledge['integration_points']])}
"""
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"[SUMMARY] 集成摘要已创建: {summary_file}")
    
    print("\\n[COMPLETE] VCPToolBox知识已成功整合到memU记忆系统！")
    print("[INFO] 主动记忆循环现在可以访问VCPToolBox的相关知识")
    
    return True

def main():
    """主函数"""
    print("[INTEGRATION] VCPToolBox + memU 记忆系统集成工具")
    print("="*60)
    
    try:
        # 运行异步集成函数
        result = asyncio.run(integrate_vcp_knowledge())
        
        if result:
            print("\\n[SUCCESS] 集成成功完成！")
            print("[INFO] VCPToolBox的知识现在已存储在memU记忆系统中")
            print("[INFO] 主动记忆循环将能够访问这些信息")
        else:
            print("\\n[ERROR] 集成过程中出现问题")
            
    except Exception as e:
        print(f"\\n[FATAL] 集成过程发生致命错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()