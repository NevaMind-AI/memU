"""
MemU SDK Usage Example

Demonstrates how to use the MemU Python SDK to interact with MemU API services.
"""

import asyncio
import os
from memu.sdk import MemuClient, MemorizeRequest
from memu.sdk.exceptions import MemuAPIException, MemuValidationException, MemuConnectionException
os.environ["MEMU_API_BASE_URL"] = "http://20.255.58.47:8000/"
os.environ["MEMU_API_KEY"] = "mu_aswH7jrXWAwu5e-muFy2e7repj7yxeasqgWnAM2h9JwiIrIz6uvFry5x-qaNgowvfgNvPAKU95Bp2NFaz7kktZABPV1heemINrcRqQ"

def basic_memorize_example():
    """Basic example of using MemU SDK to memorize conversations"""
    
    print("📝 初始化 MemU SDK 客户端...")
    
    # Initialize the client
    client = MemuClient(
        base_url=os.getenv("MEMU_API_BASE_URL"),  # Your MemU API server URL
        api_key=os.getenv("MEMU_API_KEY")
    )
    
    print(f"🔗 客户端已连接到: {client.base_url}")
    print(f"🔑 使用 API 密钥: {client.api_key[:8]}...")
    print(f"⏱️  超时设置: {client.timeout}秒")
    print(f"🔄 最大重试次数: {client.max_retries}")
    print()
    
    try:
        # Memorize a long conversation
        long_conversation = """User: Hi, I love hiking in the mountains. I've been exploring different trails in the Pacific Northwest recently.

Assistant: That sounds amazing! The Pacific Northwest has some incredible hiking opportunities. What's your favorite trail so far?

User: I really loved the Cascade Pass trail in North Cascades National Park. The views of the glaciers and peaks were breathtaking. I also did Mount Storm King in Olympic National Park last month, which was challenging but rewarding.

Assistant: Those are excellent choices! Cascade Pass is known for its stunning alpine scenery, and Mount Storm King offers that fantastic view over Lake Crescent. How long have you been hiking? Do you prefer day hikes or multi-day backpacking trips?

User: I've been hiking seriously for about 3 years now. I started with day hikes but recently got into backpacking. Last summer I did a 4-day trip on the Wonderland Trail around Mount Rainier. It was my first multi-day solo trip and really pushed my limits.

Assistant: Wow, the Wonderland Trail solo is impressive! That's a 93-mile loop with significant elevation gain. How did you prepare for that, especially mentally for the solo aspect?

User: I spent months training with weighted day hikes and shorter overnight trips. The mental preparation was harder than the physical. I practiced mindfulness and brought audiobooks for the lonely moments. The sunrise from Tolmie Peak made it all worth it though.

Assistant: That sunrise view from Tolmie Peak is legendary! It sounds like you've really developed a thoughtful approach to both the physical and mental challenges of solo backpacking. Are you planning any new adventures for this season?

User: Yes! I'm hoping to tackle the John Muir Trail in the Sierra Nevada this fall. It's been a dream of mine for years. I'm also considering getting into winter hiking with microspikes and snowshoes.

Assistant: The JMT is an incredible goal - 211 miles of some of the most beautiful wilderness in California! Fall is a great time to avoid the summer crowds. Winter hiking opens up a whole new world too. Have you looked into avalanche safety courses if you're planning to get into more serious winter mountaineering?

User: I actually signed up for an avalanche level 1 course next month. Safety is definitely my top priority, especially when hiking alone. I've also been reading about Leave No Trace principles more seriously since I want to be a responsible steward of these beautiful places.

Assistant: That's fantastic - both the avalanche course and your commitment to Leave No Trace. It's hikers like you who help preserve these wilderness areas for future generations. The education and preparation you're putting in really shows your respect for the mountains and the sport."""
        
        response = client.memorize_conversation(
            conversation_text=long_conversation,
            user_id="user_123",
            user_name="Alice Johnson",
            agent_id="agent_456", 
            agent_name="AI Assistant",
            project_id="project_789"
        )
        
        print(f"✅ Long conversation memorization started successfully!")
        print(f"📋 Task ID: {response.task_id}")
        print(f"📊 Status: {response.status}")
        print(f"💬 Message: {response.message}")
        print(f"📏 Conversation length: {len(long_conversation)} characters")
        
        # Optional: Check task status (if endpoint exists)
        try:
            status = client.get_task_status(response.task_id)
            print(f"📈 Current task status: {status}")
        except MemuAPIException as e:
            print(f"⚠️  Task status endpoint may not be implemented: {e}")
        
    except MemuValidationException as e:
        print(f"❌ Validation error: {e}")
        if e.response_data:
            print(f"   Details: {e.response_data}")
    except MemuAPIException as e:
        print(f"❌ API error: {e}")
        print(f"   Status code: {e.status_code}")
    except MemuConnectionException as e:
        print(f"❌ Connection error: {e}")
    finally:
        client.close()


def context_manager_example():
    """Example using context manager for automatic cleanup"""
    
    print("📝 使用上下文管理器初始化客户端...")
    
    with MemuClient(
        base_url=os.getenv("MEMU_API_BASE_URL", "https://api.memu.ai"),
        api_key=os.getenv("MEMU_API_KEY", "your-api-key-here")
    ) as client:
        
        print(f"✅ 上下文管理器创建成功，客户端将自动清理资源")
        
        try:
            response = client.memorize_conversation(
                conversation_text="User: I just started learning Python. Assistant: Great choice! Python is very beginner-friendly.",
                user_id="student_456",
                user_name="Bob Smith", 
                agent_id="tutor_789",
                agent_name="Python Tutor",
                project_id="education_001"
            )
            
            print(f"✅ Context manager example - Task ID: {response.task_id}")
            
        except Exception as e:
            print(f"❌ Error in context manager example: {e}")




def demonstration_mode():
    """演示模式 - 展示 SDK 功能而不实际连接服务器"""
    
    print("🎭 演示模式：展示 SDK 功能")
    print("=" * 50)
    print("注意：此模式仅演示 SDK 使用方式，不会实际连接到服务器")
    print()
    
    from memu.sdk.models import MemorizeRequest, MemorizeResponse
    
    # 演示数据模型
    print("📝 1. 数据模型演示")
    request = MemorizeRequest(
        conversation_text="用户：我喜欢爬山。助手：爬山是很好的运动！",
        user_id="user_123",
        user_name="张三",
        agent_id="agent_456",
        agent_name="AI助手", 
        api_key_id="key_789",
        project_id="project_101"
    )
    
    print(f"✅ 请求模型创建成功")
    print(f"   用户: {request.user_name} (ID: {request.user_id})")
    print(f"   代理: {request.agent_name} (ID: {request.agent_id})")
    print(f"   对话: {request.conversation_text[:50]}...")
    print(f"   项目: {request.project_id}")
    print()
    
    # 演示响应模型
    response = MemorizeResponse(
        task_id="task_abc123",
        status="pending",
        message="记忆化任务已创建"
    )
    
    print(f"✅ 响应模型创建成功")
    print(f"   任务ID: {response.task_id}")
    print(f"   状态: {response.status}")
    print(f"   消息: {response.message}")
    print()
    
    # 演示客户端配置
    print("📝 2. 客户端配置演示")
    try:
        client_config = {
            "base_url": "https://api.memu.ai",
            "api_key": "demo-key-12345",
            "timeout": 30.0,
            "max_retries": 3
        }
        
        print(f"✅ 客户端配置准备完成:")
        for key, value in client_config.items():
            if key == "api_key":
                print(f"   {key}: {str(value)[:8]}...")
            else:
                print(f"   {key}: {value}")
        print()
        
    except Exception as e:
        print(f"❌ 配置错误: {e}")
    
    print("📝 3. API 调用流程演示")
    print("   1. 初始化客户端 ✅")
    print("   2. 创建请求数据 ✅") 
    print("   3. 发送 POST 请求到 /api/v1/memory/memorize")
    print("   4. 处理响应数据")
    print("   5. 返回结果对象 ✅")
    print()
    
    print("✨ 演示完成！")
    print()
    print("💡 实际使用时:")
    print("1. 设置环境变量 MEMU_API_BASE_URL")
    print("2. 设置环境变量 MEMU_API_KEY") 
    print("3. 确保 MemU API 服务器正在运行")
    print("4. 使用真实的用户和项目数据")


if __name__ == "__main__":
    print("🌟 MemU Python SDK 示例程序")
    print("=" * 60)
    
    import sys
    
    # 检查是否有实际的 API 配置
    has_real_config = (
        os.getenv("MEMU_API_KEY") and 
        os.getenv("MEMU_API_BASE_URL") and
        os.getenv("MEMU_API_KEY") != "demo-api-key-for-testing"
    )
    
    if has_real_config:
        print("🔗 检测到真实 API 配置，运行完整示例...")
        print()
        
        print("1. 基础记忆化示例:")
        basic_memorize_example()
        
        print("\n2. 上下文管理器示例:")
        context_manager_example()
        
        
    else:
        print("🎭 未检测到真实 API 配置，运行演示模式...")
        print()
        demonstration_mode()
        print()
        
    
    print("\n" + "=" * 60)
    print("✨ 程序运行完成！")
    print("\n📚 更多信息:")
    print("- 详细文档: memu/sdk/README.md")
    print("- 测试用例: tests/test_sdk.py")
    print("- 快速开始: QUICK_START_SDK.md")
    print("- GitHub: https://github.com/NevaMind-AI/MemU")