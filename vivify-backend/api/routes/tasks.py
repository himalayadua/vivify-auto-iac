"""
Task API Routes
RESTful endpoints for task management with WebSocket support
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import Optional, List
from pydantic import BaseModel, Field
import logging
import uuid

from services.task_repository import get_task_repository
from services.websocket_manager import (
    get_websocket_manager,
    MessageType,
    broadcast_task_update,
    broadcast_task_created,
    broadcast_task_deleted
)
from services.cache import get_cache

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Request/Response Models =====

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    status: str = "todo"
    project_id: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    metadata: Optional[dict] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    metadata: Optional[dict] = None


class TaskStatusUpdate(BaseModel):
    status: str


class BatchStatusUpdate(BaseModel):
    task_ids: List[str]
    status: str


# ===== REST Endpoints =====

@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    order_by: str = Query("updated_at", regex="^(created_at|updated_at|title|status)$"),
    order_desc: bool = Query(True)
):
    """
    List tasks with optional filters
    Supports pagination and ordering
    """
    repo = get_task_repository()
    
    tasks = await repo.list_tasks(
        status=status,
        project_id=project_id,
        assignee=assignee,
        priority=priority,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_desc=order_desc
    )
    
    return {
        "tasks": tasks,
        "count": len(tasks),
        "offset": offset,
        "limit": limit
    }


@router.get("/search")
async def search_tasks(
    q: str = Query(..., min_length=1, description="Search query"),
    project_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Search tasks by title or description"""
    repo = get_task_repository()
    tasks = await repo.search_tasks(q, project_id, limit)
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get task by ID"""
    repo = get_task_repository()
    task = await repo.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return task


@router.post("", status_code=201)
async def create_task(task_data: TaskCreate):
    """Create a new task"""
    repo = get_task_repository()
    
    task = await repo.create_task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        project_id=task_data.project_id,
        assignee=task_data.assignee,
        priority=task_data.priority,
        metadata=task_data.metadata
    )
    
    # Broadcast creation via WebSocket
    await broadcast_task_created(task)
    
    return task


@router.patch("/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate):
    """Update a task"""
    repo = get_task_repository()
    
    # Filter out None values
    updates = {k: v for k, v in task_data.model_dump().items() if v is not None}
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    task = await repo.update_task(task_id, **updates)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Broadcast update via WebSocket
    await broadcast_task_update(task_id, updates)
    
    return task


@router.patch("/{task_id}/status")
async def update_task_status(task_id: str, status_data: TaskStatusUpdate):
    """Update task status (optimized endpoint for drag-drop)"""
    repo = get_task_repository()
    
    task = await repo.update_task(task_id, status=status_data.status)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Broadcast via WebSocket
    await broadcast_task_update(task_id, {"status": status_data.status})
    
    return task


@router.post("/batch/status")
async def batch_update_status(batch_data: BatchStatusUpdate):
    """
    Batch update task status (optimized for multiple drag-drop operations)
    Reduces database round-trips and WebSocket messages
    """
    repo = get_task_repository()
    
    count = await repo.batch_update_status(
        batch_data.task_ids,
        batch_data.status
    )
    
    # Broadcast batch update
    manager = get_websocket_manager()
    patches = [
        {"op": "replace", "path": f"/tasks/{task_id}/status", "value": batch_data.status}
        for task_id in batch_data.task_ids
    ]
    await manager.broadcast_to_channel(
        "tasks",
        MessageType.PATCH,
        {"patches": patches}
    )
    
    return {"updated": count, "task_ids": batch_data.task_ids}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    repo = get_task_repository()
    
    success = await repo.delete_task(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Broadcast deletion via WebSocket
    await broadcast_task_deleted(task_id)
    
    return {"message": f"Task {task_id} deleted"}


# ===== Subtask Endpoints =====

@router.post("/{task_id}/subtasks")
async def add_subtask(
    task_id: str,
    title: str = Query(..., min_length=1),
    description: str = "",
    status: str = "pending"
):
    """Add a subtask to a task"""
    repo = get_task_repository()
    
    subtask = await repo.add_subtask(task_id, title, description, status)
    
    if not subtask:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return subtask


@router.patch("/{task_id}/subtasks/{subtask_id}")
async def update_subtask(
    task_id: str,
    subtask_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None
):
    """Update a subtask"""
    repo = get_task_repository()
    
    updates = {}
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if status is not None:
        updates["status"] = status
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    subtask = await repo.update_subtask(task_id, subtask_id, **updates)
    
    if not subtask:
        raise HTTPException(status_code=404, detail=f"Subtask not found")
    
    return subtask


# ===== WebSocket Endpoint =====

@router.websocket("/stream/ws")
async def task_websocket(
    websocket: WebSocket,
    project_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time task updates
    
    Messages are batched for efficiency:
    - Individual updates are collected and sent every 100ms
    - Batch size limited to 50 messages
    - High-priority messages (create/delete) flush immediately
    """
    manager = get_websocket_manager()
    connection_id = f"ws-{uuid.uuid4().hex[:8]}"
    
    # Accept connection
    if not await manager.connect(websocket, connection_id):
        return
    
    try:
        # Subscribe to tasks channel
        channel = f"tasks:{project_id}" if project_id else "tasks"
        await manager.subscribe(connection_id, channel)
        
        # Send initial snapshot
        repo = get_task_repository()
        tasks = await repo.list_tasks(project_id=project_id)
        
        await manager.send_immediate(
            connection_id,
            MessageType.SNAPSHOT,
            {"tasks": {t["id"]: t for t in tasks}}
        )
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_json()
                msg_type = message.get("type")
                
                if msg_type == MessageType.PING:
                    await manager.send_immediate(
                        connection_id,
                        MessageType.PONG,
                        {"timestamp": message.get("timestamp")}
                    )
                elif msg_type == MessageType.SUBSCRIBE:
                    channel = message.get("channel", "tasks")
                    await manager.subscribe(connection_id, channel)
                elif msg_type == MessageType.UNSUBSCRIBE:
                    channel = message.get("channel")
                    if channel:
                        await manager.unsubscribe(connection_id, channel)
                        
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    finally:
        await manager.disconnect(connection_id)


# ===== Cache Management Endpoints =====

@router.post("/cache/invalidate")
async def invalidate_task_cache():
    """Invalidate all task caches (admin endpoint)"""
    cache = await get_cache()
    count = await cache.invalidate_all_tasks()
    return {"invalidated": count}

