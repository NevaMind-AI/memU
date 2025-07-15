# MemU API-Only Architecture Guide

MemU has been redesigned with a **clean API-only architecture** where all memory operations are performed through remote API calls. This provides better scalability, consistency, and separation of concerns.

## 🏗️ Architecture Overview

```
Client (Persona/MemoryClient) -> API -> Backend Server -> Database
```

**Key Principles:**
- **No direct database access** from client code
- **All memory operations** go through the API layer
- **Clean separation** between client and server
- **Scalable and distributed** by design

## 🚀 Quick Start

### 1. Start the API Server

```bash
# Option 1: Run directly
python server/backend/main.py

# Option 2: Use Docker
docker-compose up

# Option 3: Use the startup script
./scripts/start_api_server.sh
```

The server will run at `http://localhost:8000` by default.

### 2. Use MemU (API-Only)

```python
from memu import Persona

# Create Persona (automatically uses API)
persona = Persona(
    agent_id="my_assistant",
    personality="You are a helpful coding assistant.",
    api_url="http://localhost:8000"  # Optional - this is the default
)

# Use normally - all operations go through API
response = persona.chat("Hello!", user_id="user123")
print(response)

# End session to update memory via API
result = persona.endsession("user123")
print(f"Memory updated: {result}")
```

## 📚 API-Only Components

### Persona Class

The `Persona` class is now **API-only** by default:

```python
from memu import Persona

# All these create API-only Personas
persona1 = Persona(agent_id="assistant1")  # Uses default API URL
persona2 = Persona(agent_id="assistant2", api_url="http://localhost:8000")
persona3 = Persona(agent_id="assistant3", api_url="http://remote-server:8000")

# No more local database mode!
```

**Key Changes:**
- Removed `db_manager` parameter
- Removed `use_memo` parameter (memo not supported in API mode)
- Simplified constructor with fewer parameters
- All memory operations go through API

### MemoryClient Class

The `MemoryClient` is now a **pure API client**:

```python
from memu.memory import MemoryClient

# Create API-only memory client
client = MemoryClient(api_url="http://localhost:8000")

# All operations use API calls
memory = client.get_memory_by_agent("agent_id", "user_id")
client.update_profile("agent_id", "user_id", "New profile info")
client.update_events("agent_id", "user_id", ["New event"])
```

**Key Changes:**
- Removed all local database code
- Simplified to pure API client
- Consistent behavior regardless of deployment
- Better error handling for network issues

### Memory Class

The `Memory` class provides a unified memory interface:

```python
# Returned by MemoryClient.get_memory_by_agent()
memory = client.get_memory_by_agent("agent_id", "user_id")

# Same interface as before, but backed by API
profile = memory.get_profile()
events = memory.get_events()
mind = memory.get_mind()

# Direct API operations
memory.update_profile("New profile")
memory.update_events(["New event"])
```

## 🔄 Migration from Mixed Architecture

If you were using the previous mixed (local + API) architecture:

### Before (Mixed)
```python
# Old way - mixed local/API mode
persona_local = Persona(agent_id="test", use_memory=True)  # Local mode
persona_api = Persona(agent_id="test", api_url="http://localhost:8000")  # API mode

client_local = MemoryClient()  # Local mode
client_api = MemoryClient(api_url="http://localhost:8000")  # API mode
```

### After (API-Only)
```python
# New way - always API
persona = Persona(agent_id="test")  # Always API mode
persona_custom = Persona(agent_id="test", api_url="http://custom-server:8000")

client = MemoryClient(api_url="http://localhost:8000")  # Always API
```

## 🌟 Benefits of API-Only Architecture

### 1. **Simplified Code**
- No more conditional logic for local vs API modes
- Single code path for all operations
- Easier to understand and maintain

### 2. **Better Scalability**
- All clients can connect to the same backend
- Easy to scale horizontally
- No local database dependencies

### 3. **Consistent Behavior**
- Same behavior regardless of deployment
- No differences between local and remote modes
- Predictable performance characteristics

### 4. **Better Security**
- No direct database access from clients
- All operations go through controlled API layer
- Better audit and monitoring capabilities

### 5. **Easier Deployment**
- Clients don't need database setup
- Backend can be deployed independently
- Better separation of concerns

## 🔧 Configuration

### Default API URL
By default, MemU uses `http://localhost:8000`:

```python
# These are equivalent
persona1 = Persona(agent_id="test")
persona2 = Persona(agent_id="test", api_url="http://localhost:8000")
```

### Custom API URL
For remote deployments:

```python
persona = Persona(
    agent_id="remote_assistant",
    api_url="http://your-server.com:8000"
)
```

### Timeout Configuration
```python
from memu.memory import MemoryClient

client = MemoryClient(
    api_url="http://localhost:8000",
    timeout=60  # seconds
)
```

## 📋 API Endpoints Used

MemU clients use these API endpoints:

- `GET /api/memories` - List memories
- `GET /api/memories/{memory_id}` - Get specific memory
- `POST /api/memories/update-conversation` - Update memory with conversation
- `POST /api/memories/update-profile` - Update profile
- `POST /api/memories/update-events` - Update events
- `GET /api/memories/stats/{agent_id}` - Get memory statistics

## 🧪 Testing

Run the test suite to verify the API-only architecture:

```bash
python test_remote_api.py
```

Run the example to see it in action:

```bash
python examples/remote_api_example.py
```

## 🐳 Docker Deployment

### Development
```bash
docker-compose up
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## ❓ FAQ

### Q: Can I still use local databases?
**A:** No, the API-only architecture requires all operations to go through the API server. This provides better consistency and scalability.

### Q: What happened to memo functionality?
**A:** Memo functionality is not currently supported in API-only mode, but may be added in future versions through API endpoints.

### Q: How do I handle network failures?
**A:** The client includes timeout configuration and basic error handling. Implement retry logic in your application code as needed.

### Q: Can I use multiple API servers?
**A:** Yes, you can create different Persona instances pointing to different API servers.

### Q: Is this a breaking change?
**A:** Yes, but the migration is straightforward. Most code will work with minimal changes - just remove local database configuration.

## 🎯 Best Practices

1. **Always specify user_id** in operations
2. **Use try-catch** for network error handling
3. **Call endsession()** to update memory
4. **Use context managers** for automatic cleanup:

```python
with persona.session("user123") as session:
    response = session.chat("Hello!")
    # Memory automatically updated on exit
```

5. **Configure appropriate timeouts** for your network conditions
6. **Monitor API server health** in production deployments 