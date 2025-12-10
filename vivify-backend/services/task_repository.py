"""
Task Repository - Database-backed task storage with caching
Replaces the in-memory TaskStore with proper persistence
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
import uuid
import logging

from services.database import TaskModel, SubtaskModel, get_session
from services.cache import get_cache, cached

logger = logging.getLogger(__name__)


class TaskRepository:
    """Repository for task CRUD operations with caching"""
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "updated_at",
        order_desc: bool = True
    ) -> List[Dict]:
        """
        List tasks with optional filters
        Uses indexes for efficient filtering
        """
        cache = await get_cache()
        
        # Try cache first for simple queries
        if not assignee and not priority and offset == 0 and limit == 100:
            cached_result = await cache.get_task_list(project_id, status)
            if cached_result is not None:
                logger.debug(f"Task list cache HIT")
                return cached_result
        
        async with await get_session() as session:
            # Build query with filters
            query = select(TaskModel).options(selectinload(TaskModel.subtasks))
            
            conditions = []
            if status:
                conditions.append(TaskModel.status == status)
            if project_id:
                conditions.append(TaskModel.project_id == project_id)
            if assignee:
                conditions.append(TaskModel.assignee == assignee)
            if priority:
                conditions.append(TaskModel.priority == priority)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply ordering
            order_column = getattr(TaskModel, order_by, TaskModel.updated_at)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            task_dicts = [task.to_dict() for task in tasks]
            
            # Cache simple queries
            if not assignee and not priority and offset == 0 and limit == 100:
                await cache.set_task_list(task_dicts, project_id, status)
            
            return task_dicts
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID with subtasks"""
        cache = await get_cache()
        
        # Try cache first
        cached_result = await cache.get_task_detail(task_id)
        if cached_result is not None:
            logger.debug(f"Task detail cache HIT: {task_id}")
            return cached_result
        
        async with await get_session() as session:
            query = (
                select(TaskModel)
                .options(selectinload(TaskModel.subtasks))
                .where(TaskModel.id == task_id)
            )
            result = await session.execute(query)
            task = result.scalar_one_or_none()
            
            if task:
                task_dict = task.to_dict()
                await cache.set_task_detail(task_id, task_dict)
                return task_dict
            
            return None
    
    async def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "todo",
        project_id: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create a new task"""
        cache = await get_cache()
        
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        async with await get_session() as session:
            task = TaskModel(
                id=task_id,
                title=title,
                description=description,
                status=status,
                project_id=project_id,
                assignee=assignee,
                priority=priority,
                task_metadata=metadata or {}
            )
            session.add(task)
            await session.commit()
            await session.refresh(task, ["subtasks"])
            
            task_dict = task.to_dict()
            
            # Invalidate list caches
            await cache.invalidate_all_tasks()
            
            logger.info(f"Created task: {task_id}")
            return task_dict
    
    async def update_task(self, task_id: str, **updates) -> Optional[Dict]:
        """Update task fields"""
        cache = await get_cache()
        
        async with await get_session() as session:
            # Fetch task
            query = (
                select(TaskModel)
                .options(selectinload(TaskModel.subtasks))
                .where(TaskModel.id == task_id)
            )
            result = await session.execute(query)
            task = result.scalar_one_or_none()
            
            if not task:
                return None
            
            # Update fields
            for key, value in updates.items():
                if hasattr(task, key) and key not in ['id', 'created_at']:
                    setattr(task, key, value)
            
            task.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(task)
            
            task_dict = task.to_dict()
            
            # Invalidate caches
            await cache.invalidate_task(task_id)
            
            logger.info(f"Updated task: {task_id}")
            return task_dict
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete task and its subtasks"""
        cache = await get_cache()
        
        async with await get_session() as session:
            query = delete(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(query)
            await session.commit()
            
            if result.rowcount > 0:
                await cache.invalidate_task(task_id)
                logger.info(f"Deleted task: {task_id}")
                return True
            
            return False
    
    async def batch_update_status(
        self,
        task_ids: List[str],
        new_status: str
    ) -> int:
        """Batch update task status (optimized for WebSocket batching)"""
        cache = await get_cache()
        
        async with await get_session() as session:
            query = (
                update(TaskModel)
                .where(TaskModel.id.in_(task_ids))
                .values(status=new_status, updated_at=datetime.utcnow())
            )
            result = await session.execute(query)
            await session.commit()
            
            # Invalidate caches
            for task_id in task_ids:
                await cache.invalidate_task(task_id)
            
            logger.info(f"Batch updated {result.rowcount} tasks to status: {new_status}")
            return result.rowcount
    
    async def search_tasks(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Search tasks by title or description"""
        async with await get_session() as session:
            search_query = select(TaskModel).options(selectinload(TaskModel.subtasks))
            
            conditions = [
                or_(
                    TaskModel.title.ilike(f"%{query}%"),
                    TaskModel.description.ilike(f"%{query}%")
                )
            ]
            
            if project_id:
                conditions.append(TaskModel.project_id == project_id)
            
            search_query = (
                search_query
                .where(and_(*conditions))
                .limit(limit)
                .order_by(TaskModel.updated_at.desc())
            )
            
            result = await session.execute(search_query)
            tasks = result.scalars().all()
            
            return [task.to_dict() for task in tasks]
    
    async def add_subtask(
        self,
        task_id: str,
        title: str,
        description: str = "",
        status: str = "pending"
    ) -> Optional[Dict]:
        """Add subtask to a task"""
        cache = await get_cache()
        
        async with await get_session() as session:
            # Verify task exists
            task = await session.get(TaskModel, task_id)
            if not task:
                return None
            
            subtask = SubtaskModel(
                id=f"sub-{uuid.uuid4().hex[:8]}",
                title=title,
                description=description,
                status=status,
                task_id=task_id
            )
            session.add(subtask)
            
            # Update parent task
            task.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Invalidate cache
            await cache.invalidate_task(task_id)
            
            return subtask.to_dict()
    
    async def update_subtask(
        self,
        task_id: str,
        subtask_id: str,
        **updates
    ) -> Optional[Dict]:
        """Update a subtask"""
        cache = await get_cache()
        
        async with await get_session() as session:
            query = select(SubtaskModel).where(
                and_(
                    SubtaskModel.id == subtask_id,
                    SubtaskModel.task_id == task_id
                )
            )
            result = await session.execute(query)
            subtask = result.scalar_one_or_none()
            
            if not subtask:
                return None
            
            for key, value in updates.items():
                if hasattr(subtask, key) and key not in ['id', 'task_id']:
                    setattr(subtask, key, value)
            
            subtask.updated_at = datetime.utcnow()
            
            # Update parent task timestamp
            task = await session.get(TaskModel, task_id)
            if task:
                task.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Invalidate cache
            await cache.invalidate_task(task_id)
            
            return subtask.to_dict()


# Global repository instance
_task_repository: Optional[TaskRepository] = None


def get_task_repository() -> TaskRepository:
    """Get or create task repository"""
    global _task_repository
    if _task_repository is None:
        _task_repository = TaskRepository()
    return _task_repository

