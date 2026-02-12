import os
import subprocess
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENCLAW_PATH = r"C:\Users\16663\Desktop\openclaw\openclaw.mjs"

def call_openclaw(prompt):
    print(f"Bridge received prompt: {prompt[:100]}...")
    try:
        cmd = [
            "node", 
            OPENCLAW_PATH, 
            "agent", 
            "--message", prompt, 
            "--thinking", "low",
            "--session-id", "memu_bridge"
        ]
        # Set environment to favor English to reduce encoding issues
        env = os.environ.copy()
        env["LANG"] = "en_US.UTF-8"
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env)
        
        output = result.stdout
        # Log to file for debugging
        with open("bridge_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- PROMPT ---\n{prompt}\n")
            f.write(f"--- OUTPUT ---\n{output}\n")
            if result.stderr:
                f.write(f"--- STDERR ---\n{result.stderr}\n")

        if result.returncode != 0:
            return f"Error from OpenClaw: {result.stderr}"
            
        return output.strip()
    except Exception as e:
        return f"Bridge Exception: {str(e)}"

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    messages = data.get('messages', [])
    
    # Analyze intent
    full_request_text = " ".join([m['content'] for m in messages]).lower()
    
    # If it's a memory extraction request, force the XML format
    if "extract" in full_request_text or "memorize" in full_request_text:
        system_instruction = (
            "FORCE FORMAT: You must respond ONLY with valid XML. "
            "Use the root tag <knowledge> and child <memory> tags. "
            "Inside <memory>, include <content> and <categories> (with <category> children). "
            "Example: <knowledge><memory><content>fact</content><categories><category>knowledge</category></categories></memory></knowledge>"
        )
        prompt = system_instruction + "\n\n" + "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    else:
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    
    response_text = call_openclaw(prompt)
    
    # Post-process to ensure at least one valid root tag is present if missing
    if "<knowledge>" not in response_text and ("extract" in full_request_text or "memorize" in full_request_text):
        # Wrap the whole thing as a fallback
        response_text = f"<knowledge><memory><content>{response_text}</content><categories><category>knowledge</category></categories></memory></knowledge>"

    return jsonify({
        "id": "chatcmpl-bridge",
        "object": "chat.completion",
        "created": 123456789,
        "model": "openclaw-bridge",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    })

@app.route('/v1/embeddings', methods=['POST'])
def embeddings():
    data = request.json
    inputs = data.get('input', [])
    if isinstance(inputs, str):
        inputs = [inputs]
    results = []
    for i in range(len(inputs)):
        results.append({
            "object": "embedding",
            "index": i,
            "embedding": [0.0] * 3072
        })
    return jsonify({
        "object": "list",
        "data": results,
        "model": "fake-embeddings",
        "usage": {"prompt_tokens": 0, "total_tokens": 0}
    })

if __name__ == '__main__':
    app.run(port=5000)
