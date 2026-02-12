import requests
import json
import time

# Test the bridge with a simple chat completion request
url = "http://localhost:5000/v1/chat/completions"

headers = {
    "Content-Type": "application/json"
}

data = {
    "model": "openclaw-bridge",
    "messages": [
        {"role": "user", "content": "Hello, this is a test. Just return 'pong'."}
    ],
    "temperature": 0.7
}

print("Sending request to bridge...")
start_time = time.time()

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)  # 10 second timeout
    elapsed = time.time() - start_time
    print(f"Request completed in {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.Timeout:
    elapsed = time.time() - start_time
    print(f"Request timed out after {elapsed:.2f}s")
    print("This suggests the bridge is working but OpenClaw is taking too long to respond")
except Exception as e:
    print(f"Error: {e}")