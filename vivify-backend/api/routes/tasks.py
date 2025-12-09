"""
Task API Routes
Endpoints for task management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.task_store import get_task_store, Task

router = APIRouter()


class TaskCreate(BaseModel):
    """Request to create a task"""
    title: str
    description: Optional[str] = ""
    status: str = "todo"


class TaskUpdate(BaseModel):
    """Request to update a task"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.get("/")
async def list_tasks(status: Optional[str] = None):
    """
    List all tasks, optionally filtered by status
    """
    store = get_task_store()
    tasks = store.list_tasks(status=status)
    
    return {
        "tasks": [task.to_dict() for task in tasks]
    }


@router.get("/{task_id}")
async def get_task(task_id: str):
    """
    Get a specific task by ID
    """
    store = get_task_store()
    task = store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return task.to_dict()


@router.post("/")
async def create_task(request: TaskCreate):
    """
    Create a new task
    """
    store = get_task_store()
    task = store.create_task(
        title=request.title,
        description=request.description,
        status=request.status
    )
    
    return {
        "message": "Task created successfully",
        "task": task.to_dict()
    }


@router.patch("/{task_id}")
async def update_task(task_id: str, request: TaskUpdate):
    """
    Update a task
    """
    store = get_task_store()
    
    # Build update dict
    updates = {}
    if request.title is not None:
        updates['title'] = request.title
    if request.description is not None:
        updates['description'] = request.description
    if request.status is not None:
        updates['status'] = request.status
    
    task = store.update_task(task_id, **updates)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "message": "Task updated successfully",
        "task": task.to_dict()
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a task
    """
    store = get_task_store()
    success = store.delete_task(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "message": f"Task {task_id} deleted successfully"
    }
