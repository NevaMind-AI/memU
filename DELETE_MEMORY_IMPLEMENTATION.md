# Delete Memory API Implementation

This document summarizes the implementation of the Delete Memory API for both Python and JavaScript SDKs.

## Overview

The Delete Memory API allows users to delete memories for a given user. If an `agent_id` is provided, it deletes only that agent's memories; otherwise, it deletes all memories for the user within the project.

**API Endpoint:** `POST /api/v1/memory/delete`

## Implementation Details

### Python SDK

#### Models Added (`memu/sdk/python/models.py`)

```python
class DeleteMemoryRequest(BaseModel):
    """Request model for delete memory API"""
    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier (optional, delete all user memories if not provided)")

class DeleteMemoryResponse(BaseModel):
    """Response model for delete memory API"""
    message: str = Field(..., description="Response message")
    deleted_count: Optional[int] = Field(None, description="Number of memories deleted")
    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier (if specified)")
```

#### Method Added (`memu/sdk/python/client.py`)

```python
def delete_memories(
    self,
    user_id: str,
    agent_id: str | None = None,
) -> DeleteMemoryResponse:
    """
    Delete memories for a given user. If agent_id is provided, delete only that agent's memories; 
    otherwise delete all memories for the user within the project.

    Args:
        user_id: User identifier
        agent_id: Agent identifier (optional, delete all user memories if not provided)

    Returns:
        DeleteMemoryResponse: Response with deletion status and count

    Raises:
        MemuValidationException: For validation errors
        MemuAPIException: For API errors
        MemuConnectionException: For connection errors
    """
```

### JavaScript SDK

#### Models Added (`memu/sdk/javascript/src/models.ts`)

```typescript
export interface DeleteMemoryRequest {
  /** User identifier */
  userId: string;
  /** Agent identifier (optional, delete all user memories if not provided) */
  agentId?: string;
}

export interface DeleteMemoryResponse {
  /** Response message */
  message: string;
  /** Number of memories deleted */
  deletedCount?: number;
  /** User identifier */
  userId: string;
  /** Agent identifier (if specified) */
  agentId?: string;
}
```

#### Method Added (`memu/sdk/javascript/src/client.ts`)

```typescript
async deleteMemories(options: {
  userId: string;
  agentId?: string;
}): Promise<DeleteMemoryResponse> {
  // Implementation details...
}
```

## Usage Examples

### Python

```python
from memu import MemuClient

client = MemuClient(
    base_url="https://api.memu.so",
    api_key="your-api-key"
)

# Delete all memories for a user
response = client.delete_memories(user_id="user123")
print(f"Deleted {response.deleted_count} memories for user {response.user_id}")

# Delete memories for a specific user and agent
response = client.delete_memories(
    user_id="user123",
    agent_id="agent456"
)
print(f"Deleted {response.deleted_count} memories for user {response.user_id} and agent {response.agent_id}")
```

### JavaScript

```javascript
import { MemuClient } from 'memu-js';

const client = new MemuClient({
  baseUrl: 'https://api.memu.so',
  apiKey: 'your-api-key'
});

// Delete all memories for a user
const response1 = await client.deleteMemories({
  userId: "user123"
});
console.log(`Deleted ${response1.deletedCount} memories for user ${response1.userId}`);

// Delete memories for a specific user and agent
const response2 = await client.deleteMemories({
  userId: "user123",
  agentId: "agent456"
});
console.log(`Deleted ${response2.deletedCount} memories for user ${response2.userId} and agent ${response2.agentId}`);
```

## Files Created/Modified

### New Files
- `example/client/delete_memory.py` - Python usage example
- `example/client/delete_memory.js` - JavaScript usage example
- `example/client/delete_memory.ts` - TypeScript usage example
- `example/client/test_delete_memory.py` - Test script for validation
- `DELETE_MEMORY_IMPLEMENTATION.md` - This documentation

### Modified Files
- `memu/sdk/python/models.py` - Added DeleteMemoryRequest and DeleteMemoryResponse models
- `memu/sdk/python/client.py` - Added delete_memories method and imports
- `memu/sdk/javascript/src/models.ts` - Added DeleteMemoryRequest and DeleteMemoryResponse interfaces
- `memu/sdk/javascript/src/client.ts` - Added deleteMemories method and imports
- `docs/API_REFERENCE.md` - Added documentation for the new API

## Error Handling

The implementation includes comprehensive error handling for:
- **Validation Errors** - Invalid request parameters
- **Authentication Errors** - Invalid or missing API key
- **Connection Errors** - Network issues or server unavailability
- **API Errors** - Server-side errors

## Testing

A test script (`test_delete_memory.py`) is included to validate:
- Model validation for request and response objects
- Method signature verification
- Basic functionality testing

## Documentation

The API reference documentation has been updated to include:
- Complete method documentation with parameters and return types
- Usage examples for both Python and JavaScript
- Data model definitions
- Error handling information

## Next Steps

1. **Integration Testing** - Test with actual MemU server
2. **Performance Testing** - Verify performance with large datasets
3. **Security Review** - Ensure proper access controls
4. **User Feedback** - Gather feedback from SDK users
