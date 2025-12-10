"""
Tests for database models and indexes
Verifies SQLAlchemy models work correctly with proper indexing
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from services.database import (
    Base, TaskModel, SubtaskModel, GCPResourceCacheModel,
    init_database, get_session, close_database
)


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create a test session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        yield session


class TestTaskModel:
    """Tests for TaskModel"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, test_session):
        """Test creating a task"""
        task = TaskModel(
            id="task-test-1",
            title="Test Task",
            description="Test description",
            status="todo",
            project_id="test-project"
        )
        test_session.add(task)
        await test_session.commit()
        
        # Verify task was created
        result = await test_session.get(TaskModel, "task-test-1")
        assert result is not None
        assert result.title == "Test Task"
        assert result.status == "todo"
    
    @pytest.mark.asyncio
    async def test_task_to_dict(self, test_session):
        """Test task serialization"""
        task = TaskModel(
            id="task-test-2",
            title="Serialization Test",
            status="inprogress",
            priority="high",
            assignee="test-user"
        )
        test_session.add(task)
        await test_session.commit()
        
        # Refresh to avoid lazy loading issues
        await test_session.refresh(task, ["subtasks"])
        task_dict = task.to_dict()
        
        assert task_dict["id"] == "task-test-2"
        assert task_dict["title"] == "Serialization Test"
        assert task_dict["status"] == "inprogress"
        assert task_dict["priority"] == "high"
        assert task_dict["assignee"] == "test-user"
        assert "created_at" in task_dict
        assert "updated_at" in task_dict
    
    @pytest.mark.asyncio
    async def test_task_with_subtasks(self, test_session):
        """Test task with subtasks relationship"""
        task = TaskModel(
            id="task-test-3",
            title="Task with Subtasks",
            status="todo"
        )
        test_session.add(task)
        await test_session.commit()
        
        subtask1 = SubtaskModel(
            id="sub-1",
            title="Subtask 1",
            status="pending",
            task_id="task-test-3"
        )
        subtask2 = SubtaskModel(
            id="sub-2",
            title="Subtask 2",
            status="completed",
            task_id="task-test-3"
        )
        test_session.add_all([subtask1, subtask2])
        await test_session.commit()
        
        # Refresh to load relationships with explicit attribute list
        await test_session.refresh(task, ["subtasks"])
        
        task_dict = task.to_dict()
        assert len(task_dict["subtasks"]) == 2


class TestDatabaseIndexes:
    """Tests to verify indexes are created correctly"""
    
    @pytest.mark.asyncio
    async def test_task_indexes_exist(self, test_engine):
        """Verify all expected indexes exist on tasks table"""
        expected_indexes = [
            "idx_tasks_status",
            "idx_tasks_project_id",
            "idx_tasks_project_status",
            "idx_tasks_updated_at",
            "idx_tasks_created_at",
            "idx_tasks_project_updated",
            "idx_tasks_assignee",
            "idx_tasks_priority",
        ]
        
        async with test_engine.connect() as conn:
            # Get indexes using SQLite pragma
            result = await conn.execute(text("PRAGMA index_list(tasks)"))
            indexes = [row[1] for row in result.fetchall()]
            
            for expected in expected_indexes:
                assert expected in indexes, f"Index {expected} not found"
    
    @pytest.mark.asyncio
    async def test_subtask_indexes_exist(self, test_engine):
        """Verify indexes on subtasks table"""
        expected_indexes = [
            "idx_subtasks_task_id",
            "idx_subtasks_task_status",
        ]
        
        async with test_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA index_list(subtasks)"))
            indexes = [row[1] for row in result.fetchall()]
            
            for expected in expected_indexes:
                assert expected in indexes, f"Index {expected} not found"
    
    @pytest.mark.asyncio
    async def test_gcp_cache_indexes_exist(self, test_engine):
        """Verify indexes on GCP cache table"""
        expected_indexes = [
            "idx_gcp_cache_project",
            "idx_gcp_cache_type",
            "idx_gcp_cache_project_type",
            "idx_gcp_cache_region",
            "idx_gcp_cache_expires",
        ]
        
        async with test_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA index_list(gcp_resource_cache)"))
            indexes = [row[1] for row in result.fetchall()]
            
            for expected in expected_indexes:
                assert expected in indexes, f"Index {expected} not found"


class TestQueryPerformance:
    """Tests to verify queries use indexes efficiently"""
    
    @pytest.mark.asyncio
    async def test_status_filter_uses_index(self, test_engine, test_session):
        """Verify status filter query uses index"""
        # Create multiple tasks
        for i in range(100):
            task = TaskModel(
                id=f"perf-task-{i}",
                title=f"Task {i}",
                status="todo" if i % 3 == 0 else "inprogress",
                project_id="perf-project"
            )
            test_session.add(task)
        await test_session.commit()
        
        # Check query plan uses index
        async with test_engine.connect() as conn:
            result = await conn.execute(
                text("EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE status = 'todo'")
            )
            plan = str(result.fetchall())
            # SQLite should show index usage
            assert "idx_tasks_status" in plan or "USING INDEX" in plan.upper() or "SEARCH" in plan.upper()
    
    @pytest.mark.asyncio
    async def test_composite_filter_uses_index(self, test_engine, test_session):
        """Verify composite project+status filter uses index"""
        async with test_engine.connect() as conn:
            result = await conn.execute(
                text("EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE project_id = 'test' AND status = 'todo'")
            )
            plan = str(result.fetchall())
            # Should use the composite index
            assert "idx_tasks_project_status" in plan or "USING INDEX" in plan.upper() or "SEARCH" in plan.upper()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

