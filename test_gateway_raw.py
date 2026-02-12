import requests
import json

def test():
    # Local Gateway Token
    api_key = "85e6fe825bf8aeda981522de74315ab71b4c27103f31c8f6"
    url = "http://localhost:18789/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "openclaw",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "stream": False
    }
    
    print(f"Calling {url}...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", response.json()['choices'][0]['message']['content'])
        else:
            print("Error Details:", response.text)
    except Exception as e:
        print("Request failed:", e)

if __name__ == "__main__":
    test()
