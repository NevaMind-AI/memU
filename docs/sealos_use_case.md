# 🛡️ Context-Aware Support Agent (Sealos Edition)

## Overview
This use case demonstrates how MemU enables a support agent to remember user history across sessions, deployed on a Sealos Devbox environment. It showcases the persistence and context-retrieval capabilities of the MemU engine without relying on external cloud storage.

## Quick Start

### Prerequisites
- Sealos Devbox Environment
- Python 3.13+
- MemU Library (installed via `make install`)

### Run the Demo
```bash
uv run python examples/sealos_support_agent.py
```

## Live Demo Output

Below is the actual output captured from the Sealos terminal during the Hackathon:
```text
🚀 Starting Sealos Support Agent Demo (Offline Mode)

📝 --- Phase 1: Ingesting Conversation History ---
👤 Captain: "I'm getting a 502 Bad Gateway error on port 3000."
🤖 Agent: (Memorizing this interaction...)
✅ Memory stored! extracted 2 items.
   - [profile] Captain reported a 502 Bad Gateway error on port 3000.
   - [event] Captain reported a 502 Bad Gateway error on port 3000.

🔍 --- Phase 2: Retrieval on New Interaction ---
👤 Captain: "Hello"
🤖 Agent: (Searching memory for context...)

💡 Retrieved Context:
   Found Memory: Captain reported a 502 Bad Gateway error on port 3000.
   Found Memory: Captain reported a 502 Bad Gateway error on port 3000.

💬 --- Phase 3: Agent Response ---
🤖 Agent: "Welcome back, Captain. I see you had a 502 error on port 3000 recently. Is that resolved?"

✨ Demo Completed Successfully
```

## Code Highlights

- **MockLLM Implementation:** We implemented a custom `MockLLM` class to simulate the LLM provider. This ensures the demo is 100% reproducible in offline or restricted environments without requiring an OpenAI API Key.

- **Sealos Integration:** The agent is optimized to run within the ephemeral nature of Sealos Devbox containers.
