"""
Tests for Task API endpoints
Integration tests for the REST API
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch, MagicMock
import json


# Create test app
@pytest.fixture
def test_app():
    """Create test FastAPI app"""
    from api.routes.tasks import router
    
    app = FastAPI()
    app.include_router(router, prefix="/api/tasks")
    
    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


@pytest.fixture
def mock_repo():
    """Create mock task repository"""
    repo = MagicMock()
    repo.list_tasks = AsyncMock(return_value=[
        {"id": "task-1", "title": "Task 1", "status": "todo"},
        {"id": "task-2", "title": "Task 2", "status": "inprogress"},
    ])
    repo.get_task = AsyncMock(return_value={
        "id": "task-1",
        "title": "Task 1",
        "description": "Description",
        "status": "todo"
    })
    repo.create_task = AsyncMock(return_value={
        "id": "task-new",
        "title": "New Task",
        "status": "todo"
    })
    repo.update_task = AsyncMock(return_value={
        "id": "task-1",
        "title": "Updated Task",
        "status": "done"
    })
    repo.delete_task = AsyncMock(return_value=True)
    repo.search_tasks = AsyncMock(return_value=[
        {"id": "task-1", "title": "Search Result"}
    ])
    repo.batch_update_status = AsyncMock(return_value=3)
    return repo


class TestTaskListEndpoint:
    """Tests for GET /api/tasks"""
    
    def test_list_tasks(self, client, mock_repo):
        """Test listing all tasks"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks")
            
            assert response.status_code == 200
            data = response.json()
            assert "tasks" in data
            assert len(data["tasks"]) == 2
            assert data["count"] == 2
    
    def test_list_tasks_with_status_filter(self, client, mock_repo):
        """Test filtering tasks by status"""
        mock_repo.list_tasks = AsyncMock(return_value=[
            {"id": "task-1", "title": "Task 1", "status": "todo"}
        ])
        
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks?status=todo")
            
            assert response.status_code == 200
            mock_repo.list_tasks.assert_called_once()
            call_kwargs = mock_repo.list_tasks.call_args.kwargs
            assert call_kwargs["status"] == "todo"
    
    def test_list_tasks_with_pagination(self, client, mock_repo):
        """Test task list pagination"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks?limit=10&offset=20")
            
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 20


class TestTaskDetailEndpoint:
    """Tests for GET /api/tasks/{task_id}"""
    
    def test_get_task(self, client, mock_repo):
        """Test getting a single task"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks/task-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "task-1"
            assert data["title"] == "Task 1"
    
    def test_get_task_not_found(self, client, mock_repo):
        """Test getting non-existent task"""
        mock_repo.get_task = AsyncMock(return_value=None)
        
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks/nonexistent")
            
            assert response.status_code == 404


class TestTaskCreateEndpoint:
    """Tests for POST /api/tasks"""
    
    def test_create_task(self, client, mock_repo):
        """Test creating a new task"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            with patch('api.routes.tasks.broadcast_task_created', new_callable=AsyncMock):
                response = client.post("/api/tasks", json={
                    "title": "New Task",
                    "description": "Task description",
                    "status": "todo"
                })
                
                assert response.status_code == 201
                data = response.json()
                assert data["title"] == "New Task"
    
    def test_create_task_validation_error(self, client, mock_repo):
        """Test validation error on create"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.post("/api/tasks", json={
                "title": "",  # Empty title should fail
            })
            
            assert response.status_code == 422


class TestTaskUpdateEndpoint:
    """Tests for PATCH /api/tasks/{task_id}"""
    
    def test_update_task(self, client, mock_repo):
        """Test updating a task"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            with patch('api.routes.tasks.broadcast_task_update', new_callable=AsyncMock):
                response = client.patch("/api/tasks/task-1", json={
                    "title": "Updated Title",
                    "status": "done"
                })
                
                assert response.status_code == 200
    
    def test_update_task_not_found(self, client, mock_repo):
        """Test updating non-existent task"""
        mock_repo.update_task = AsyncMock(return_value=None)
        
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            with patch('api.routes.tasks.broadcast_task_update', new_callable=AsyncMock):
                response = client.patch("/api/tasks/nonexistent", json={
                    "status": "done"
                })
                
                assert response.status_code == 404
    
    def test_update_task_status_only(self, client, mock_repo):
        """Test status-only update endpoint"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            with patch('api.routes.tasks.broadcast_task_update', new_callable=AsyncMock):
                response = client.patch("/api/tasks/task-1/status", json={
                    "status": "done"
                })
                
                assert response.status_code == 200


class TestTaskDeleteEndpoint:
    """Tests for DELETE /api/tasks/{task_id}"""
    
    def test_delete_task(self, client, mock_repo):
        """Test deleting a task"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            with patch('api.routes.tasks.broadcast_task_deleted', new_callable=AsyncMock):
                response = client.delete("/api/tasks/task-1")
                
                assert response.status_code == 200
    
    def test_delete_task_not_found(self, client, mock_repo):
        """Test deleting non-existent task"""
        mock_repo.delete_task = AsyncMock(return_value=False)
        
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.delete("/api/tasks/nonexistent")
            
            assert response.status_code == 404


class TestBatchOperations:
    """Tests for batch operations"""
    
    def test_batch_update_status(self, client, mock_repo):
        """Test batch status update"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            with patch('api.routes.tasks.get_websocket_manager') as mock_ws:
                mock_ws.return_value.broadcast_to_channel = AsyncMock()
                
                response = client.post("/api/tasks/batch/status", json={
                    "task_ids": ["task-1", "task-2", "task-3"],
                    "status": "done"
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["updated"] == 3


class TestSearchEndpoint:
    """Tests for GET /api/tasks/search"""
    
    def test_search_tasks(self, client, mock_repo):
        """Test searching tasks"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks/search?q=test")
            
            assert response.status_code == 200
            data = response.json()
            assert "tasks" in data
    
    def test_search_requires_query(self, client, mock_repo):
        """Test search requires query parameter"""
        with patch('api.routes.tasks.get_task_repository', return_value=mock_repo):
            response = client.get("/api/tasks/search")
            
            assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

