"""
Memory数据库存储层模块。

根据STRUCTURE.md设计，实现Memory对象的数据库存储和管理：
- memories表：存储Memory基础信息和元数据
- memory_contents表：统一存储画像和事件内容
- 支持完整的Memory CRUD操作
"""

import json
import hashlib
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base import Memory, ProfileMemory, EventMemory


class MemoryRepository:
    """
    Memory数据库操作仓库。
    
    提供Memory对象的完整数据库存储和管理功能。
    """
    
    def __init__(self, db_path: str = "memory.db"):
        """
        初始化数据库连接。
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 创建memories表（统一Memory表）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    
                    -- Theory of Mind 分析结果
                    tom_metadata TEXT,
                    confidence_score REAL,
                    
                    -- 记忆统计信息
                    profile_content_hash TEXT,
                    event_count INTEGER DEFAULT 0,
                    last_event_date TEXT,
                    
                    -- 索引
                    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
                )
            """)
            
            # 创建memory_contents表（Memory内容表）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_contents (
                    content_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    content_type TEXT NOT NULL CHECK (content_type IN ('profile', 'event')),
                    
                    -- 内容数据
                    content_data TEXT NOT NULL,
                    content_text TEXT,
                    content_hash TEXT,
                    
                    -- 元数据
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    
                    FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
                    UNIQUE(memory_id, content_type)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_contents_memory_type ON memory_contents(memory_id, content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_contents_hash ON memory_contents(content_hash)")
            
            conn.commit()
    
    def save_memory(self, memory: Memory) -> bool:
        """
        保存完整Memory对象到数据库。
        
        Args:
            memory: Memory对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 1. 保存Memory基础信息
                memory_data = {
                    'memory_id': memory.memory_id,
                    'agent_id': memory.agent_id,
                    'created_at': memory.created_at.isoformat(),
                    'updated_at': memory.updated_at.isoformat(),
                    'tom_metadata': json.dumps(memory.tom_metadata) if memory.tom_metadata else None,
                    'profile_content_hash': self._calculate_hash(memory.get_profile_content()),
                    'event_count': len(memory.get_event_content()),
                    'last_event_date': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO memories 
                    (memory_id, agent_id, created_at, updated_at, tom_metadata, 
                     profile_content_hash, event_count, last_event_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_data['memory_id'],
                    memory_data['agent_id'],
                    memory_data['created_at'],
                    memory_data['updated_at'],
                    memory_data['tom_metadata'],
                    memory_data['profile_content_hash'],
                    memory_data['event_count'],
                    memory_data['last_event_date']
                ))
                
                # 2. 保存ProfileMemory内容
                if memory.get_profile_content():
                    self._save_profile_content(conn, memory.memory_id, memory.profile_memory)
                
                # 3. 保存EventMemory内容
                if memory.get_event_content():
                    self._save_event_content(conn, memory.memory_id, memory.event_memory)
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving memory: {e}")
            return False
    
    def load_memory(self, memory_id: str) -> Optional[Memory]:
        """
        从数据库加载完整Memory对象。
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Optional[Memory]: Memory对象，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 1. 加载Memory基础信息
                memory_row = conn.execute("""
                    SELECT * FROM memories WHERE memory_id = ?
                """, [memory_id]).fetchone()
                
                if not memory_row:
                    return None
                
                # 2. 创建Memory对象
                memory = Memory(
                    agent_id=memory_row['agent_id'],
                    memory_id=memory_id
                )
                memory.created_at = datetime.fromisoformat(memory_row['created_at'])
                memory.updated_at = datetime.fromisoformat(memory_row['updated_at'])
                
                if memory_row['tom_metadata']:
                    memory.tom_metadata = json.loads(memory_row['tom_metadata'])
                
                # 3. 加载ProfileMemory内容
                profile_content = self._load_profile_content(conn, memory_id)
                if profile_content:
                    memory.profile_memory = ProfileMemory(profile_content)
                
                # 4. 加载EventMemory内容
                event_content = self._load_event_content(conn, memory_id)
                if event_content:
                    memory.event_memory = EventMemory(event_content)
                
                return memory
                
        except Exception as e:
            print(f"Error loading memory: {e}")
            return None
    
    def load_memory_by_agent(self, agent_id: str) -> Optional[Memory]:
        """
        根据Agent ID加载Memory。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Memory]: Memory对象，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 查找该Agent的最新Memory
                memory_row = conn.execute("""
                    SELECT memory_id FROM memories 
                    WHERE agent_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT 1
                """, [agent_id]).fetchone()
                
                if memory_row:
                    return self.load_memory(memory_row['memory_id'])
                
                return None
                
        except Exception as e:
            print(f"Error loading memory by agent: {e}")
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        删除Memory对象。
        
        Args:
            memory_id: Memory ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 删除memory_contents
                conn.execute("DELETE FROM memory_contents WHERE memory_id = ?", [memory_id])
                
                # 删除memories
                conn.execute("DELETE FROM memories WHERE memory_id = ?", [memory_id])
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def list_memories_by_agent(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        列出指定Agent的Memory记录。
        
        Args:
            agent_id: Agent ID
            limit: 返回数量限制
            
        Returns:
            List[Dict]: Memory信息列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                rows = conn.execute("""
                    SELECT memory_id, created_at, updated_at, event_count, confidence_score
                    FROM memories 
                    WHERE agent_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, [agent_id, limit]).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []
    
    def _save_profile_content(self, conn: sqlite3.Connection, memory_id: str, profile_memory: ProfileMemory):
        """保存画像记忆内容"""
        content_data = {
            "paragraph": profile_memory.get_content()
        }
        
        content_id = f"{memory_id}_profile"
        content_text = profile_memory.get_content()
        content_hash = self._calculate_hash(content_text)
        
        conn.execute("""
            INSERT OR REPLACE INTO memory_contents 
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (?, ?, 'profile', ?, ?, ?, ?, ?)
        """, [
            content_id,
            memory_id,
            json.dumps(content_data),
            content_text,
            content_hash,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ])
    
    def _save_event_content(self, conn: sqlite3.Connection, memory_id: str, event_memory: EventMemory):
        """保存事件记忆内容"""
        content_data = {
            "events": event_memory.get_content(),
            "max_events": event_memory.max_events
        }
        
        content_id = f"{memory_id}_event"
        content_text = ' '.join(event_memory.get_content())
        content_hash = self._calculate_hash(content_text)
        
        conn.execute("""
            INSERT OR REPLACE INTO memory_contents 
            (content_id, memory_id, content_type, content_data, content_text, content_hash, created_at, updated_at)
            VALUES (?, ?, 'event', ?, ?, ?, ?, ?)
        """, [
            content_id,
            memory_id,
            json.dumps(content_data),
            content_text,
            content_hash,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ])
    
    def _load_profile_content(self, conn: sqlite3.Connection, memory_id: str) -> Optional[str]:
        """加载画像记忆内容"""
        row = conn.execute("""
            SELECT content_data FROM memory_contents 
            WHERE memory_id = ? AND content_type = 'profile'
        """, [memory_id]).fetchone()
        
        if row:
            content_data = json.loads(row[0])
            return content_data.get('paragraph', '')
        
        return None
    
    def _load_event_content(self, conn: sqlite3.Connection, memory_id: str) -> Optional[List[str]]:
        """加载事件记忆内容"""
        row = conn.execute("""
            SELECT content_data FROM memory_contents 
            WHERE memory_id = ? AND content_type = 'event'
        """, [memory_id]).fetchone()
        
        if row:
            content_data = json.loads(row[0])
            return content_data.get('events', [])
        
        return None
    
    def _calculate_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        获取Memory统计信息。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict: 统计信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 基础统计
                stats_row = conn.execute("""
                    SELECT 
                        COUNT(*) as total_memories,
                        MAX(updated_at) as last_updated,
                        SUM(event_count) as total_events
                    FROM memories 
                    WHERE agent_id = ?
                """, [agent_id]).fetchone()
                
                return {
                    'agent_id': agent_id,
                    'total_memories': stats_row['total_memories'],
                    'last_updated': stats_row['last_updated'],
                    'total_events': stats_row['total_events'] or 0
                }
                
        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {} 