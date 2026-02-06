import asyncio
import os
from openai import AsyncOpenAI

async def test():
    # Local Gateway Token
    api_key = "85e6fe825bf8aeda981522de74315ab71b4c27103f31c8f6"
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="http://localhost:18789/v1"
    )
    
    print("Testing local gateway Chat...")
    try:
        response = await client.chat.completions.create(
            model="google-antigravity/gemini-3-flash",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print("Chat response:", response.choices[0].message.content)
    except Exception as e:
        print("Chat error:", e)

if __name__ == "__main__":
    asyncio.run(test())
