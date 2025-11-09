"""
Task Management Tool
"""

from langchain.tools import BaseTool
from services.task_store import get_task_store
from typing import Optional
import json


class TaskTool(BaseTool):
    name: str = "task_manager"
    description: str = """
    Manage tasks in the Kanban board. This tool allows you to view, create, update, and delete tasks.
    
    Operations:
    - list: List all tasks (optional filter by status: todo, inprogress, inreview, done)
    - get: Get details of a specific task by ID
    - create: Create a new task
    - update: Update a task's status or details
    - delete: Delete a task
    
    Input should be a JSON string with 'operation' and relevant parameters.
    
    Examples:
    - List all tasks: {"operation": "list"}
    - List inprogress tasks: {"operation": "list", "status": "inprogress"}
    - Get task details: {"operation": "get", "task_id": "task-1"}
    - Create task: {"operation": "create", "title": "New task", "description": "Details", "status": "todo"}
    - Update task: {"operation": "update", "task_id": "task-1", "status": "done"}
    - Delete task: {"operation": "delete", "task_id": "task-1"}
    """
    
    def __init__(self):
        super().__init__()
        object.__setattr__(self, '_store', get_task_store())
    
    def _run(self, query: str) -> str:
        """Execute task operation"""
        store = getattr(self, '_store')
        try:
            params = json.loads(query)
            operation = params.get("operation")
            
            if operation == "list":
                status = params.get("status")
                tasks = store.list_tasks(status=status)
                
                if not tasks:
                    return f"No tasks found{' with status ' + status if status else ''}."
                
                result = []
                for t in tasks:
                    result.append({
                        "id": t.id,
                        "title": t.title,
                        "status": t.status,
                        "description": t.description[:100] if t.description else ""
                    })
                
                return json.dumps(result, indent=2)
            
            elif operation == "get":
                task_id = params.get("task_id")
                task = store.get_task(task_id)
                
                if not task:
                    return f"Task {task_id} not found."
                
                return json.dumps(task.to_dict(), indent=2)
            
            elif operation == "create":
                title = params.get("title")
                description = params.get("description", "")
                status = params.get("status", "todo")
                
                if not title:
                    return "Error: 'title' is required to create a task."
                
                task = store.create_task(
                    title=title,
                    description=description,
                    status=status
                )
                
                return f"✅ Created task: '{task.title}' (ID: {task.id}, Status: {task.status})"
            
            elif operation == "update":
                task_id = params.get("task_id")
                
                if not task_id:
                    return "Error: 'task_id' is required to update a task."
                
                # Remove operation and task_id from params
                update_params = {k: v for k, v in params.items() if k not in ["operation", "task_id"]}
                
                task = store.update_task(task_id, **update_params)
                
                if not task:
                    return f"Task {task_id} not found."
                
                return f"✅ Updated task: '{task.title}' (ID: {task.id}, Status: {task.status})"
            
            elif operation == "delete":
                task_id = params.get("task_id")
                
                if not task_id:
                    return "Error: 'task_id' is required to delete a task."
                
                success = store.delete_task(task_id)
                
                if success:
                    return f"✅ Deleted task {task_id}"
                else:
                    return f"Task {task_id} not found."
            
            else:
                return f"Unknown operation: {operation}. Valid operations: list, get, create, update, delete"
        
        except json.JSONDecodeError:
            return "Error: Invalid JSON input. Please provide a valid JSON string."
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version"""
        return self._run(query)
