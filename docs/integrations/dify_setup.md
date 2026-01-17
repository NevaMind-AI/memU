# Dify Integration Setup Guide

Integrate MemU with Dify to give your agents long-term memory capabilities.

## 1. Hosting the Adapter

Since MemU is a Python library, you need to run a small API server to expose it to Dify.

### Prerequisites
- Python 3.13+
- `memu-py` installed
- `fastapi` and `uvicorn` installed

### Server Code (`server.py`)

Create a `server.py` file with the following content. This mounts the MemU Dify Adapter.

```python
import uvicorn
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from memu import MemUService
from memu.integrations.dify_adapter import router as dify_router, get_memu_service

# Configuration
API_KEY = "memu-secret-key"  # Change this!
HOST = "0.0.0.0"
PORT = 8000

# Global service instance
memu_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memu_service
    # Initialize MemU (ensure env vars like OPENAI_API_KEY are set)
    memu_service = MemUService()
    yield

def get_service_override():
    return memu_service

app = FastAPI(lifespan=lifespan)

# Mount the Dify Adapter Router
app.include_router(dify_router)

# Override the dependency to provide our initialized service
app.dependency_overrides[get_memu_service] = get_service_override

if __name__ == "__main__":
    print(f"Starting MemU Adapter on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
```

Run the server:
```bash
export OPENAI_API_KEY=sk-...
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 2. Configuring Dify

1. **Open Dify**: Navigate to your Dify dashboard.
2. **Create Custom Tool**:
   - Go to **Tools** > **API-based Tool** > **Create**.
3. **Import Specification**:
   - Copy the content of [`dify-openapi-spec.yaml`](./dify-openapi-spec.yaml).
   - Paste it into the "Schema" editor in Dify.
   - **Important**: Update the `servers` URL in the YAML if your server is not running on `localhost` (e.g., use your public IP or ngrok URL).
4. **Authentication**:
   - Choose **Bearer Auth**.
   - Input the API Key you set in `server.py` (e.g., `memu-secret-key`).
5. **Save**.

## 3. Using in Agents

1. Go to your Agent's **Orchestration** page.
2. Click **Add Tool** and select **MemU Dify Integration**.
3. Enable both `add_memory` and `search_memory`.
4. **System Prompt Instruction**:
   Add this to your agent's instructions:
   > Use `add_memory` to save important facts, preferences, or events the user mentions.

## 4. Troubleshooting

### Connection Refused
- **Cause**: Dify cannot reach the MemU adapter.
- **Solution**:
  - If using Docker, use `host.docker.internal` instead of `localhost`.
  - Ensure the server is running on `0.0.0.0` (not just `127.0.0.1`).

### Empty Results from Search
- **Cause**: No memories match the query or `user_id` mismatch.
- **Solution**:
  - Verify the `user_id` passed by Dify matches what was used to store memories.
  - Check MemU logs for query execution details.

### 422 Validation Error
- **Cause**: Missing `query` parameter or incorrect JSON format.
- **Solution**: Ensure Dify is identifying the tool arguments correctly in the prompt configuration.
