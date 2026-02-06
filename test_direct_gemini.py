import os
import requests
import json

def test():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found")
        return
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": "Hello, how are you?"}]
        }]
    }
    
    print("Testing direct Gemini API...")
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("Success!")
        print(response.json()['candidates'][0]['content']['parts'][0]['text'])
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    test()
