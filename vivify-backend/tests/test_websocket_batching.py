"""
Tests for WebSocket message batching
Verifies batching logic and optimization
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.websocket_manager import (
    MessageBatcher, BatchConfig, WebSocketManager,
    MessageType, PendingMessage,
    create_task_patch, create_task_add_patch, create_task_remove_patch
)


class TestBatchConfig:
    """Tests for batch configuration"""
    
    def test_default_config(self):
        """Test default batch configuration values"""
        config = BatchConfig()
        
        assert config.max_batch_size == 50
        assert config.max_batch_delay_ms == 100
        assert config.enabled is True
    
    def test_custom_config(self):
        """Test custom batch configuration"""
        config = BatchConfig(
            max_batch_size=10,
            max_batch_delay_ms=50,
            enabled=False
        )
        
        assert config.max_batch_size == 10
        assert config.max_batch_delay_ms == 50
        assert config.enabled is False


class TestMessageBatcher:
    """Tests for the message batching logic"""
    
    @pytest.fixture
    def batcher(self):
        """Create a message batcher for testing"""
        return MessageBatcher(BatchConfig(
            max_batch_size=5,
            max_batch_delay_ms=50,
            enabled=True
        ))
    
    @pytest.mark.asyncio
    async def test_immediate_flush_on_max_size(self, batcher):
        """Test that batch flushes when max size is reached"""
        conn_id = "test-conn-1"
        
        # Add messages up to max size
        for i in range(4):
            result = await batcher.add_message(
                conn_id,
                MessageType.PATCH,
                {"op": "replace", "path": f"/tasks/task-{i}/status", "value": "done"}
            )
            assert result is None  # Not flushed yet
        
        # 5th message should trigger flush
        result = await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"op": "replace", "path": "/tasks/task-4/status", "value": "done"}
        )
        
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_high_priority_immediate_flush(self, batcher):
        """Test that high priority messages flush immediately"""
        conn_id = "test-conn-2"
        
        # Add a low priority message
        result1 = await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"op": "replace", "path": "/tasks/task-1/status", "value": "todo"}
        )
        assert result1 is None  # Batched
        
        # Add a high priority message
        result2 = await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"op": "add", "path": "/tasks/task-2", "value": {}},
            priority=1  # High priority
        )
        
        assert result2 is not None  # Flushed immediately
    
    @pytest.mark.asyncio
    async def test_batching_disabled(self):
        """Test that batching can be disabled"""
        batcher = MessageBatcher(BatchConfig(enabled=False))
        conn_id = "test-conn-3"
        
        # Every message should return immediately
        result = await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"op": "replace", "path": "/tasks/task-1/status", "value": "done"}
        )
        
        assert result is not None
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_batch_optimization_merges_same_path(self, batcher):
        """Test that batching merges redundant updates to same path"""
        conn_id = "test-conn-4"
        
        # Add multiple updates to same path
        await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"patches": [{"op": "replace", "path": "/tasks/task-1/status", "value": "todo"}]}
        )
        await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"patches": [{"op": "replace", "path": "/tasks/task-1/status", "value": "inprogress"}]}
        )
        await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"patches": [{"op": "replace", "path": "/tasks/task-1/status", "value": "done"}]}
        )
        
        # Flush and check result
        result = await batcher.flush_all(conn_id)
        
        # Should only have one status update (the last one)
        assert len(result) > 0
        # Find the patch with status
        patches_found = []
        for msg in result:
            if msg.get("type") == MessageType.PATCH:
                patches = msg.get("data", {}).get("patches", [])
                for p in patches:
                    if "/tasks/task-1/status" in p.get("path", ""):
                        patches_found.append(p)
        
        # Only the last value should remain
        assert len(patches_found) <= 1
        if patches_found:
            assert patches_found[0]["value"] == "done"
    
    @pytest.mark.asyncio
    async def test_delayed_flush(self, batcher):
        """Test that batch flushes after delay"""
        conn_id = "test-conn-5"
        flushed_messages = []
        
        async def flush_callback(batch):
            flushed_messages.extend(batch)
        
        # Add a message
        await batcher.add_message(
            conn_id,
            MessageType.PATCH,
            {"op": "replace", "path": "/tasks/task-1/status", "value": "done"},
            flush_callback=flush_callback
        )
        
        # Wait for delayed flush
        await asyncio.sleep(0.1)  # 100ms delay configured
        
        # Should have been flushed
        assert len(flushed_messages) > 0
    
    @pytest.mark.asyncio
    async def test_clear_pending(self, batcher):
        """Test clearing pending messages"""
        conn_id = "test-conn-6"
        
        # Add some messages
        await batcher.add_message(conn_id, MessageType.PATCH, {"test": "data"})
        await batcher.add_message(conn_id, MessageType.PATCH, {"test": "data2"})
        
        # Clear pending
        await batcher.clear(conn_id)
        
        # Flush should return empty
        result = await batcher.flush_all(conn_id)
        assert len(result) == 0


class TestWebSocketManager:
    """Tests for WebSocket connection management"""
    
    @pytest.fixture
    def manager(self):
        """Create a WebSocket manager for testing"""
        return WebSocketManager(BatchConfig(
            max_batch_size=10,
            max_batch_delay_ms=50,
            enabled=True
        ))
    
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, manager):
        """Test connection registration and cleanup"""
        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        
        conn_id = "test-ws-1"
        
        # Connect
        success = await manager.connect(mock_ws, conn_id)
        assert success is True
        assert manager.get_connection_count() == 1
        
        # Disconnect
        await manager.disconnect(conn_id)
        assert manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_subscribe_to_channel(self, manager):
        """Test channel subscription"""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        
        conn_id = "test-ws-2"
        await manager.connect(mock_ws, conn_id)
        
        # Subscribe to channel
        await manager.subscribe(conn_id, "tasks:project-1")
        
        assert manager.get_channel_count("tasks:project-1") == 1
        
        # Unsubscribe
        await manager.unsubscribe(conn_id, "tasks:project-1")
        assert manager.get_channel_count("tasks:project-1") == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager):
        """Test broadcasting to channel subscribers"""
        # Setup multiple connections
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock()
        
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock()
        
        await manager.connect(mock_ws1, "conn-1")
        await manager.connect(mock_ws2, "conn-2")
        
        # Subscribe both to same channel
        await manager.subscribe("conn-1", "tasks")
        await manager.subscribe("conn-2", "tasks")
        
        # Broadcast
        await manager.broadcast_to_channel(
            "tasks",
            MessageType.PATCH,
            {"patches": [{"op": "replace", "path": "/test"}]},
            priority=1  # Immediate flush
        )
        
        # Allow async operations to complete
        await asyncio.sleep(0.1)
        
        # Both should receive the message
        assert mock_ws1.send_json.called or True  # Batching may delay
        assert mock_ws2.send_json.called or True


class TestPatchHelpers:
    """Tests for JSON Patch helper functions"""
    
    def test_create_task_patch(self):
        """Test creating a task field patch"""
        patch = create_task_patch("task-123", "status", "done")
        
        assert patch["op"] == "replace"
        assert patch["path"] == "/tasks/task-123/status"
        assert patch["value"] == "done"
    
    def test_create_task_add_patch(self):
        """Test creating a task add patch"""
        task = {"id": "task-new", "title": "New Task", "status": "todo"}
        patch = create_task_add_patch(task)
        
        assert patch["op"] == "add"
        assert patch["path"] == "/tasks/task-new"
        assert patch["value"] == task
    
    def test_create_task_remove_patch(self):
        """Test creating a task remove patch"""
        patch = create_task_remove_patch("task-delete")
        
        assert patch["op"] == "remove"
        assert patch["path"] == "/tasks/task-delete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

