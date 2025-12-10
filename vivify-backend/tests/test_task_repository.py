"""
Tests for Task Repository
Verifies CRUD operations and caching integration
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from services.task_repository import TaskRepository, get_task_repository
from services.database import Base, TaskModel, SubtaskModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Setup test database"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    yield engine, async_session
    
    await engine.dispose()


@pytest.fixture
def mock_cache():
    """Create a mock cache service"""
    cache = AsyncMock()
    cache.get_task_list = AsyncMock(return_value=None)
    cache.set_task_list = AsyncMock(return_value=True)
    cache.get_task_detail = AsyncMock(return_value=None)
    cache.set_task_detail = AsyncMock(return_value=True)
    cache.invalidate_task = AsyncMock(return_value=1)
    cache.invalidate_all_tasks = AsyncMock(return_value=5)
    return cache


class TestTaskRepository:
    """Tests for TaskRepository CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, test_db, mock_cache):
        """Test creating a new task"""
        engine, session_factory = test_db
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                task = await repo.create_task(
                    title="Test Task",
                    description="Test Description",
                    status="todo",
                    project_id="project-1",
                    assignee="user-1",
                    priority="high"
                )
                
                assert task is not None
                assert task["title"] == "Test Task"
                assert task["status"] == "todo"
                assert task["project_id"] == "project-1"
                assert task["id"].startswith("task-")
                
                # Verify cache was invalidated
                mock_cache.invalidate_all_tasks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task_from_cache(self, mock_cache):
        """Test getting task from cache"""
        cached_task = {
            "id": "task-cached",
            "title": "Cached Task",
            "status": "inprogress"
        }
        mock_cache.get_task_detail = AsyncMock(return_value=cached_task)
        
        with patch('services.task_repository.get_cache', return_value=mock_cache):
            with patch('services.task_repository.get_session'):
                repo = TaskRepository()
                
                task = await repo.get_task("task-cached")
                
                assert task == cached_task
                # Session should not be used when cache hits
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, test_db, mock_cache):
        """Test listing tasks with various filters"""
        engine, session_factory = test_db
        
        # Create test tasks
        async with session_factory() as session:
            tasks = [
                TaskModel(id="task-1", title="Task 1", status="todo", project_id="proj-1"),
                TaskModel(id="task-2", title="Task 2", status="inprogress", project_id="proj-1"),
                TaskModel(id="task-3", title="Task 3", status="todo", project_id="proj-2"),
            ]
            for t in tasks:
                session.add(t)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                # Filter by status
                todo_tasks = await repo.list_tasks(status="todo")
                assert len(todo_tasks) == 2
                
                # Filter by project
                proj1_tasks = await repo.list_tasks(project_id="proj-1")
                assert len(proj1_tasks) == 2
                
                # Combined filters
                proj1_todo = await repo.list_tasks(project_id="proj-1", status="todo")
                assert len(proj1_todo) == 1
    
    @pytest.mark.asyncio
    async def test_update_task(self, test_db, mock_cache):
        """Test updating a task"""
        engine, session_factory = test_db
        
        # Create test task
        async with session_factory() as session:
            task = TaskModel(id="task-update", title="Original", status="todo")
            session.add(task)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                updated = await repo.update_task(
                    "task-update",
                    title="Updated Title",
                    status="inprogress"
                )
                
                assert updated is not None
                assert updated["title"] == "Updated Title"
                assert updated["status"] == "inprogress"
                
                # Verify cache was invalidated
                mock_cache.invalidate_task.assert_called_with("task-update")
    
    @pytest.mark.asyncio
    async def test_delete_task(self, test_db, mock_cache):
        """Test deleting a task"""
        engine, session_factory = test_db
        
        # Create test task
        async with session_factory() as session:
            task = TaskModel(id="task-delete", title="To Delete", status="todo")
            session.add(task)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                success = await repo.delete_task("task-delete")
                assert success is True
                
                # Verify cache was invalidated
                mock_cache.invalidate_task.assert_called_with("task-delete")
                
                # Verify task is gone
                task = await repo.get_task("task-delete")
                assert task is None
    
    @pytest.mark.asyncio
    async def test_batch_update_status(self, test_db, mock_cache):
        """Test batch updating task status"""
        engine, session_factory = test_db
        
        # Create test tasks
        async with session_factory() as session:
            tasks = [
                TaskModel(id="batch-1", title="Batch 1", status="todo"),
                TaskModel(id="batch-2", title="Batch 2", status="todo"),
                TaskModel(id="batch-3", title="Batch 3", status="todo"),
            ]
            for t in tasks:
                session.add(t)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                count = await repo.batch_update_status(
                    ["batch-1", "batch-2"],
                    "done"
                )
                
                assert count == 2
                
                # Verify caches were invalidated for each task
                assert mock_cache.invalidate_task.call_count == 2
    
    @pytest.mark.asyncio
    async def test_search_tasks(self, test_db, mock_cache):
        """Test searching tasks by title/description"""
        engine, session_factory = test_db
        
        # Create test tasks
        async with session_factory() as session:
            tasks = [
                TaskModel(id="search-1", title="Setup CI/CD Pipeline", description="Configure GitHub Actions"),
                TaskModel(id="search-2", title="Database Migration", description="Migrate to PostgreSQL"),
                TaskModel(id="search-3", title="API Documentation", description="Write Swagger docs"),
            ]
            for t in tasks:
                session.add(t)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                # Search by title
                results = await repo.search_tasks("Pipeline")
                assert len(results) == 1
                assert results[0]["id"] == "search-1"
                
                # Search by description
                results = await repo.search_tasks("PostgreSQL")
                assert len(results) == 1
                assert results[0]["id"] == "search-2"
    
    @pytest.mark.asyncio
    async def test_add_subtask(self, test_db, mock_cache):
        """Test adding a subtask to a task"""
        engine, session_factory = test_db
        
        # Create parent task
        async with session_factory() as session:
            task = TaskModel(id="parent-task", title="Parent Task", status="todo")
            session.add(task)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                subtask = await repo.add_subtask(
                    "parent-task",
                    title="Subtask 1",
                    description="Subtask description",
                    status="pending"
                )
                
                assert subtask is not None
                assert subtask["title"] == "Subtask 1"
                assert subtask["task_id"] == "parent-task"
                
                # Verify cache was invalidated
                mock_cache.invalidate_task.assert_called_with("parent-task")


class TestTaskRepositoryPagination:
    """Tests for pagination and ordering"""
    
    @pytest.mark.asyncio
    async def test_pagination(self, test_db, mock_cache):
        """Test task list pagination"""
        engine, session_factory = test_db
        
        # Create many tasks
        async with session_factory() as session:
            for i in range(25):
                task = TaskModel(id=f"page-task-{i}", title=f"Task {i}", status="todo")
                session.add(task)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                # First page
                page1 = await repo.list_tasks(limit=10, offset=0)
                assert len(page1) == 10
                
                # Second page
                page2 = await repo.list_tasks(limit=10, offset=10)
                assert len(page2) == 10
                
                # Third page (partial)
                page3 = await repo.list_tasks(limit=10, offset=20)
                assert len(page3) == 5
    
    @pytest.mark.asyncio
    async def test_ordering(self, test_db, mock_cache):
        """Test task list ordering"""
        engine, session_factory = test_db
        
        # Create tasks with different titles
        async with session_factory() as session:
            tasks = [
                TaskModel(id="order-c", title="Charlie", status="todo"),
                TaskModel(id="order-a", title="Alpha", status="todo"),
                TaskModel(id="order-b", title="Bravo", status="todo"),
            ]
            for t in tasks:
                session.add(t)
            await session.commit()
        
        with patch('services.task_repository.get_session', return_value=session_factory()):
            with patch('services.task_repository.get_cache', return_value=mock_cache):
                repo = TaskRepository()
                
                # Order by title ascending
                tasks = await repo.list_tasks(order_by="title", order_desc=False)
                assert tasks[0]["title"] == "Alpha"
                assert tasks[1]["title"] == "Bravo"
                assert tasks[2]["title"] == "Charlie"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

