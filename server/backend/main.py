"""
PersonaLab Backend Management System - FastAPI Backend

Provides API interfaces for conversation, memory and memory operation records in the database
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

# Set PostgreSQL environment variables (before importing PersonaLab modules)
def setup_postgres_env():
    """Set PostgreSQL environment variables"""
    # Get default configuration from setup script
    default_config = {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'personalab',
        'POSTGRES_USER': 'chenhong',
        'POSTGRES_PASSWORD': ''
    }
    
    # Only set default values when environment variables are not set
    for key, value in default_config.items():
        if not os.getenv(key):
            os.environ[key] = value
    
    print(f"🔧 PostgreSQL Configuration:")
    print(f"   POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
    print(f"   POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}")
    print(f"   POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
    print(f"   POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
    print(f"   POSTGRES_PASSWORD: {'*' * len(os.getenv('POSTGRES_PASSWORD', ''))}")

# Set environment variables
setup_postgres_env()

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from personalab.config.database import get_database_manager
from personalab.memory.manager import MemoryClient
from personalab.memo.manager import ConversationManager

app = FastAPI(
    title="PersonaLab Backend Management System",
    description="Provides API interfaces for conversation, memory and memory operation records in the database",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
db_manager = get_database_manager()
memory_client = MemoryClient(db_manager=db_manager)
conversation_manager = ConversationManager(db_manager=db_manager)

# Pydantic models
class SystemStats(BaseModel):
    conversations: Dict[str, int]
    memories: Dict[str, int]
    agents: Dict[str, int]
    users: Dict[str, int]

class ConversationInfo(BaseModel):
    conversation_id: str
    agent_id: str
    user_id: str
    created_at: datetime
    turn_count: Optional[int] = 0
    summary: Optional[str] = None
    session_id: Optional[str] = None
    memory_id: Optional[str] = None

class MemoryInfo(BaseModel):
    memory_id: str
    agent_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    profile_content: Optional[str] = None
    event_count: Optional[int] = 0
    mind_metadata: Optional[Dict] = None

class MemoryOperation(BaseModel):
    operation_id: str
    memory_id: str
    agent_id: str
    user_id: str
    operation_type: str
    timestamp: datetime
    details: str

class DeleteResponse(BaseModel):
    success: bool
    message: str

# API routes
@app.get("/", response_model=Dict[str, str])
async def root():
    """Health check"""
    return {"message": "PersonaLab Backend Management System API", "status": "running"}

@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """Get system statistics"""
    try:
        stats = get_system_stats()
        return SystemStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations", response_model=List[ConversationInfo])
async def get_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get conversation list"""
    try:
        # Get conversation list
        conversations_data = []
        
        if agent_id:
            conversations_data = conversation_manager.get_conversation_history(
                agent_id=agent_id, 
                limit=per_page * page,
                user_id=user_id if user_id else None
            )
        else:
            conversations_data = get_all_conversations(limit=per_page * page)
        
        # Pagination handling
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_conversations = conversations_data[start_idx:end_idx]
        
        return [ConversationInfo(**conv) for conv in paginated_conversations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: str):
    """Get conversation details"""
    try:
        conversation = conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return {
            "conversation_id": conversation.conversation_id,
            "agent_id": conversation.agent_id,
            "user_id": conversation.user_id,
            "created_at": conversation.created_at,
            "turn_count": conversation.turn_count,
            "summary": conversation.summary,
            "session_id": conversation.session_id,
            "memory_id": conversation.memory_id,
            "messages": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "message_index": msg.message_index,
                    "created_at": msg.created_at
                }
                for msg in conversation.messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}", response_model=DeleteResponse)
async def delete_conversation(conversation_id: str):
    """Delete conversation"""
    try:
        success = conversation_manager.delete_conversation(conversation_id)
        if success:
            return DeleteResponse(success=True, message="Conversation deleted successfully")
        else:
            return DeleteResponse(success=False, message="Deletion failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memories", response_model=List[MemoryInfo])
async def get_memories(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get memory list"""
    try:
        memories_data = get_all_memories(agent_id=agent_id or '', user_id=user_id or '', limit=per_page * page)
        
        # Pagination handling
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_memories = memories_data[start_idx:end_idx]
        
        return [MemoryInfo(**memory) for memory in paginated_memories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memories/{memory_id}")
async def get_memory_detail(memory_id: str):
    """Get memory details"""
    try:
        memory = memory_client.database.load_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        return {
            'memory_id': memory.memory_id,
            'agent_id': memory.agent_id,
            'user_id': memory.user_id,
            'created_at': memory.created_at,
            'updated_at': memory.updated_at,
            'profile_content': memory.get_profile_content(),
            'event_content': memory.get_event_content(),
            'mind_content': memory.get_mind_content(),
            'mind_metadata': memory.mind_metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memories/{memory_id}", response_model=DeleteResponse)
async def delete_memory(memory_id: str):
    """Delete memory"""
    try:
        success = memory_client.database.delete_memory(memory_id)
        if success:
            return DeleteResponse(success=True, message="Memory deleted successfully")
        else:
            return DeleteResponse(success=False, message="Deletion failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory-operations", response_model=List[MemoryOperation])
async def get_memory_operations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """Get memory operation records"""
    try:
        operations = get_memory_operations(limit=per_page * page)
        
        # Pagination handling
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_operations = operations[start_idx:end_idx]
        
        return [MemoryOperation(**op) for op in paginated_operations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents", response_model=List[str])
async def get_agents():
    """Get all unique agent list"""
    try:
        return get_unique_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users", response_model=List[str])
async def get_users():
    """Get all unique user list"""
    try:
        return get_unique_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def get_db_connection_string():
    """Get database connection string"""
    try:
        # Build connection_string from connection_params
        params = db_manager.config.connection_params
        
        # Check if connection_string already exists
        if 'connection_string' in params:
            return params['connection_string']
        
        # Build connection_string from parameters
        host = params.get('host', 'localhost')
        port = params.get('port', '5432')
        dbname = params.get('dbname', 'personalab')
        user = params.get('user', 'postgres')
        password = params.get('password', '')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    except Exception as e:
        print(f"Error getting database config: {e}")
        return None

def get_system_stats():
    """Get system statistics"""
    stats = {
        'conversations': {
            'total': 0,
            'today': 0,
            'this_week': 0
        },
        'memories': {
            'total': 0,
            'updated_today': 0,
            'updated_this_week': 0
        },
        'agents': {
            'total': 0,
            'active_today': 0
        },
        'users': {
            'total': 0,
            'active_today': 0
        }
    }
    
    try:
        # Get conversation statistics
        all_conversations = get_all_conversations(limit=1000)
        stats['conversations']['total'] = len(all_conversations)
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        today_conversations = [c for c in all_conversations 
                             if parse_date(c.get('created_at', '')).date() == today]
        stats['conversations']['today'] = len(today_conversations)
        
        week_conversations = [c for c in all_conversations 
                            if parse_date(c.get('created_at', '')).date() >= week_ago]
        stats['conversations']['this_week'] = len(week_conversations)
        
        # Get memory statistics
        all_memories = get_all_memories(limit=1000)
        stats['memories']['total'] = len(all_memories)
        
        today_memories = [m for m in all_memories 
                        if parse_date(m.get('updated_at', '')).date() == today]
        stats['memories']['updated_today'] = len(today_memories)
        
        week_memories = [m for m in all_memories 
                       if parse_date(m.get('updated_at', '')).date() >= week_ago]
        stats['memories']['updated_this_week'] = len(week_memories)
        
        # Get agent and user statistics
        agents = get_unique_agents()
        users = get_unique_users()
        stats['agents']['total'] = len(agents)
        stats['users']['total'] = len(users)
        
        # Active agents and users today
        active_agents_today = set(c.get('agent_id') for c in today_conversations)
        active_users_today = set(c.get('user_id') for c in today_conversations)
        stats['agents']['active_today'] = len(active_agents_today)
        stats['users']['active_today'] = len(active_users_today)
        
    except Exception as e:
        print(f"Error getting stats: {e}")
    
    return stats

def get_all_conversations(limit=100):
    """Get basic information of all conversations"""
    try:
        import psycopg2
        import psycopg2.extras
        
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT conversation_id, agent_id, user_id, created_at, 
                           turn_count, summary, session_id, memory_id
                    FROM conversations 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []

def get_all_memories(agent_id='', user_id='', limit=100):
    """Get basic information of all memories"""
    try:
        import psycopg2
        import psycopg2.extras
        
        query = """
            SELECT memory_id, agent_id, user_id, created_at, updated_at,
                   profile_content, event_count, mind_metadata
            FROM memories 
        """
        params = []
        conditions = []
        
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY updated_at DESC LIMIT %s"
        params.append(limit)
        
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error getting memories: {e}")
        return []

def get_memory_operations(limit=100):
    """Get memory operation records"""
    try:
        import psycopg2
        import psycopg2.extras
        
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT memory_id, agent_id, user_id, updated_at, created_at,
                           profile_content, event_count,
                           CASE 
                               WHEN created_at = updated_at THEN 'CREATE'
                               ELSE 'UPDATE'
                           END as operation_type
                    FROM memories 
                    ORDER BY updated_at DESC 
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                
                operations = []
                for row in rows:
                    operations.append({
                        'operation_id': f"{row['memory_id']}_{int(row['updated_at'].timestamp())}",
                        'memory_id': row['memory_id'],
                        'agent_id': row['agent_id'],
                        'user_id': row['user_id'],
                        'operation_type': row['operation_type'],
                        'timestamp': row['updated_at'],
                        'details': f"Profile length: {len(row['profile_content'] or '')}, Events: {row['event_count']}"
                    })
                
                return operations
    except Exception as e:
        print(f"Error getting memory operations: {e}")
        return []

def get_unique_agents():
    """Get all unique agent list"""
    try:
        import psycopg2
        
        agents = set()
        
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT agent_id FROM conversations WHERE agent_id IS NOT NULL")
                agents.update(row[0] for row in cur.fetchall())
                
                cur.execute("SELECT DISTINCT agent_id FROM memories WHERE agent_id IS NOT NULL")
                agents.update(row[0] for row in cur.fetchall())
        
        return sorted(list(agents))
    except Exception as e:
        print(f"Error getting agents: {e}")
        return []

def get_unique_users():
    """Get all unique user list"""
    try:
        import psycopg2
        
        users = set()
        
        connection_string = get_db_connection_string()
        if not connection_string:
            return []
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT user_id FROM conversations WHERE user_id IS NOT NULL")
                users.update(row[0] for row in cur.fetchall())
                
                cur.execute("SELECT DISTINCT user_id FROM memories WHERE user_id IS NOT NULL")
                users.update(row[0] for row in cur.fetchall())
        
        return sorted(list(users))
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

def parse_date(date_str):
    """Parse date string"""
    try:
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            # Try multiple date formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                try:
                    return datetime.strptime(date_str.split('.')[0], fmt)
                except ValueError:
                    continue
        return datetime.now()
    except:
        return datetime.now()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 