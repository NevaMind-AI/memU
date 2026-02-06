import requests
import json

# Test the bridge with a simple chat completion request
url = "http://localhost:5000/v1/chat/completions"

headers = {
    "Content-Type": "application/json"
}

data = {
    "model": "openclaw-bridge",
    "messages": [
        {"role": "user", "content": "Hello, are you working?"}
    ],
    "temperature": 0.7
}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")