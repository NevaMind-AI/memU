"""
Task Service

Service for managing background tasks and their status.
"""

import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ...utils.logging import get_logger

logger = get_logger(__name__)


class TaskService:
    """Service for managing task state and status"""
    
    def __init__(self):
        """Initialize task service with in-memory storage"""
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_task(self, task_type: str, task_data: Dict[str, Any]) -> str:
        """
        Create a new task
        
        Args:
            task_type: Type of task (e.g., 'memorize')
            task_data: Task-specific data
            
        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        task = {
            "id": task_id,
            "type": task_type,
            "status": "PENDING",
            "data": task_data,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now
        }
        
        with self._lock:
            self._tasks[task_id] = task
        
        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict with task information or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update task status and result
        
        Args:
            task_id: Task identifier
            status: New status (PENDING, PROCESSING, SUCCESS, FAILURE)
            result: Task result data
            error: Error message if failed
            
        Returns:
            bool: True if task was updated, False if not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            task["status"] = status
            task["updated_at"] = datetime.now()
            
            if result is not None:
                task["result"] = result
            
            if error is not None:
                task["error"] = error
        
        logger.info(f"Updated task {task_id} to status {status}")
        return True
    
    def list_tasks(self, task_type: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all tasks, optionally filtered by type
        
        Args:
            task_type: Optional task type filter
            
        Returns:
            Dict of tasks
        """
        with self._lock:
            if task_type is None:
                return self._tasks.copy()
            else:
                return {
                    task_id: task 
                    for task_id, task in self._tasks.items() 
                    if task["type"] == task_type
                }
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up completed tasks older than specified age
        
        Args:
            max_age_hours: Maximum age in hours for completed tasks
            
        Returns:
            int: Number of tasks cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._lock:
            tasks_to_remove = []
            
            for task_id, task in self._tasks.items():
                if (
                    task["status"] in ["SUCCESS", "FAILURE"] 
                    and task["updated_at"] < cutoff_time
                ):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} completed tasks")
        
        return cleaned_count
