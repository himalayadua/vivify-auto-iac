"""
Task Store - In-memory storage for tasks
Will be replaced with database later
"""

from typing import List, Optional, Dict
from datetime import datetime
import json


class Task:
    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        status: str = "todo",
        created_at: str = None,
        updated_at: str = None,
        subtasks: List = None,
        metadata: Dict = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.subtasks = subtasks or []
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "subtasks": self.subtasks,
            "metadata": self.metadata
        }


class TaskStore:
    """In-memory task storage"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Initialize with mock tasks"""
        mock_tasks = [
            Task(
                id="task-1",
                title="Setup CI/CD Pipeline",
                description="Configure GitHub Actions for automated testing and deployment",
                status="inprogress",
                subtasks=[
                    {"id": "sub-1", "title": "Create workflow file", "status": "completed"},
                    {"id": "sub-2", "title": "Configure secrets", "status": "pending"}
                ],
                metadata={"priority": "high", "assignee": "DevOps Team"}
            ),
            Task(
                id="task-2",
                title="Configure Monitoring",
                description="Set up Prometheus and Grafana for infrastructure monitoring",
                status="inprogress",
                subtasks=[
                    {"id": "sub-3", "title": "Install Prometheus", "status": "completed"},
                    {"id": "sub-4", "title": "Create dashboards", "status": "pending"}
                ],
                metadata={"priority": "high", "assignee": "SRE Team"}
            ),
            Task(
                id="task-3",
                title="Deploy to Production",
                description="Deploy the application to production environment",
                status="inprogress",
                metadata={"priority": "critical", "assignee": "DevOps Team"}
            ),
            Task(
                id="task-4",
                title="Update Documentation",
                description="Update API documentation and deployment guides",
                status="todo",
                metadata={"priority": "medium", "assignee": "Tech Writer"}
            ),
            Task(
                id="task-5",
                title="Security Audit",
                description="Perform security audit of the infrastructure",
                status="todo",
                metadata={"priority": "high", "assignee": "Security Team"}
            ),
            Task(
                id="task-6",
                title="Database Migration",
                description="Migrate database to new schema version",
                status="done",
                metadata={"priority": "high", "assignee": "Backend Team"}
            ),
            Task(
                id="task-7",
                title="Load Testing",
                description="Perform load testing on production environment",
                status="inreview",
                metadata={"priority": "medium", "assignee": "QA Team"}
            )
        ]
        
        for task in mock_tasks:
            self.tasks[task.id] = task
    
    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """List all tasks, optionally filtered by status"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID"""
        return self.tasks.get(task_id)
    
    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "todo"
    ) -> Task:
        """Create a new task"""
        # Generate new ID
        task_ids = [int(t.id.split('-')[1]) for t in self.tasks.values()]
        new_id = f"task-{max(task_ids) + 1 if task_ids else 1}"
        
        task = Task(
            id=new_id,
            title=title,
            description=description,
            status=status
        )
        
        self.tasks[new_id] = task
        return task
    
    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update a task"""
        task = self.tasks.get(task_id)
        
        if not task:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now().isoformat()
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False


# Global instance
_task_store = None

def get_task_store() -> TaskStore:
    """Get or create task store instance"""
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
    return _task_store
