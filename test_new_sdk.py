import os
from google import genai

def test():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found")
        return
        
    client = genai.Client(api_key=api_key)
    
    print("Testing new Google GenAI SDK...")
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents='Say hello'
        )
        print("Success!")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
