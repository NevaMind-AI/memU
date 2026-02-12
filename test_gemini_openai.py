import asyncio
import os
from openai import AsyncOpenAI

async def test():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found")
        return
        
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    print("Testing Chat...")
    try:
        response = await client.chat.completions.create(
            model="gemini-1.5-flash",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print("Chat response:", response.choices[0].message.content)
    except Exception as e:
        print("Chat error:", e)

    print("\nTesting Embedding...")
    try:
        # For Gemini OpenAI endpoint, the embedding model name might be different
        # Let's try text-embedding-004
        response = await client.embeddings.create(
            model="text-embedding-004",
            input="Hello world"
        )
        print("Embedding size:", len(response.data[0].embedding))
    except Exception as e:
        print("Embedding error:", e)

if __name__ == "__main__":
    asyncio.run(test())
