"""
WebSocket Manager with Message Batching
Implements efficient message batching for task updates
"""

import asyncio
import json
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    SNAPSHOT = "snapshot"
    PATCH = "patch"
    BATCH_PATCH = "batch_patch"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


@dataclass
class BatchConfig:
    """Configuration for message batching"""
    # Maximum messages to batch together
    max_batch_size: int = 50
    # Maximum time to wait before flushing batch (milliseconds)
    max_batch_delay_ms: int = 100
    # Enable/disable batching
    enabled: bool = True


@dataclass
class PendingMessage:
    """A message waiting to be batched"""
    type: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # Higher = more urgent, flush immediately


class MessageBatcher:
    """
    Batches WebSocket messages for efficient transmission
    
    Instead of sending each update immediately, messages are collected
    and sent as batches to reduce network overhead and improve performance.
    """
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self._pending: Dict[str, List[PendingMessage]] = defaultdict(list)
        self._flush_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def add_message(
        self,
        connection_id: str,
        message_type: str,
        data: Any,
        priority: int = 0,
        flush_callback: Callable = None
    ) -> Optional[List[Dict]]:
        """
        Add message to batch
        
        Args:
            connection_id: Unique ID for the WebSocket connection
            message_type: Type of message
            data: Message data
            priority: 0=normal, 1+=high priority (flush immediately)
            flush_callback: Async callback to send messages
            
        Returns:
            Batched messages if batch is ready to flush, None otherwise
        """
        if not self.config.enabled:
            # Batching disabled, return single message immediately
            return [{"type": message_type, "data": data}]
        
        async with self._lock:
            message = PendingMessage(
                type=message_type,
                data=data,
                priority=priority
            )
            self._pending[connection_id].append(message)
            
            # Check if we should flush immediately
            should_flush = (
                priority > 0 or
                len(self._pending[connection_id]) >= self.config.max_batch_size
            )
            
            if should_flush:
                return await self._flush(connection_id)
            
            # Schedule delayed flush if not already scheduled
            if connection_id not in self._flush_tasks or self._flush_tasks[connection_id].done():
                self._flush_tasks[connection_id] = asyncio.create_task(
                    self._delayed_flush(connection_id, flush_callback)
                )
            
            return None
    
    async def _delayed_flush(
        self,
        connection_id: str,
        flush_callback: Callable = None
    ):
        """Flush batch after delay"""
        await asyncio.sleep(self.config.max_batch_delay_ms / 1000)
        
        async with self._lock:
            if connection_id in self._pending and self._pending[connection_id]:
                batch = await self._flush(connection_id)
                if batch and flush_callback:
                    await flush_callback(batch)
    
    async def _flush(self, connection_id: str) -> List[Dict]:
        """Flush pending messages for a connection"""
        if connection_id not in self._pending:
            return []
        
        messages = self._pending.pop(connection_id, [])
        
        if not messages:
            return []
        
        # Optimize: merge consecutive patches for the same path
        optimized = self._optimize_batch(messages)
        
        if len(optimized) == 1:
            return optimized
        
        # Return as batch
        return [{
            "type": MessageType.BATCH_PATCH,
            "data": {
                "patches": optimized,
                "count": len(optimized),
                "timestamp": datetime.utcnow().isoformat()
            }
        }]
    
    def _optimize_batch(self, messages: List[PendingMessage]) -> List[Dict]:
        """
        Optimize batch by merging redundant operations
        
        For example, if we have:
        - replace /tasks/1/status = "todo"
        - replace /tasks/1/status = "inprogress"
        
        We only keep the last one.
        """
        # Group patches by path
        path_patches: Dict[str, PendingMessage] = {}
        other_messages: List[Dict] = []
        
        for msg in messages:
            if msg.type == MessageType.PATCH:
                patches = msg.data.get("patches", [msg.data])
                for patch in patches:
                    path = patch.get("path", "")
                    # For replace/add operations, only keep the last one per path
                    if patch.get("op") in ("replace", "add"):
                        path_patches[path] = patch
                    elif patch.get("op") == "remove":
                        # Remove operations should be applied
                        path_patches[path] = patch
                    else:
                        # Keep other operations as-is
                        other_messages.append({"type": msg.type, "data": patch})
            else:
                other_messages.append({"type": msg.type, "data": msg.data})
        
        # Combine optimized patches
        result = other_messages
        if path_patches:
            result.append({
                "type": MessageType.PATCH,
                "data": {"patches": list(path_patches.values())}
            })
        
        return result
    
    async def flush_all(self, connection_id: str) -> List[Dict]:
        """Force flush all pending messages for a connection"""
        async with self._lock:
            # Cancel any pending flush task
            if connection_id in self._flush_tasks:
                self._flush_tasks[connection_id].cancel()
                del self._flush_tasks[connection_id]
            
            return await self._flush(connection_id)
    
    async def clear(self, connection_id: str):
        """Clear pending messages for a connection"""
        async with self._lock:
            if connection_id in self._flush_tasks:
                self._flush_tasks[connection_id].cancel()
                del self._flush_tasks[connection_id]
            self._pending.pop(connection_id, None)


class WebSocketManager:
    """
    Manages WebSocket connections with message batching
    
    Features:
    - Connection tracking
    - Room/channel subscriptions
    - Message batching for efficiency
    - Broadcast support
    """
    
    def __init__(self, batch_config: BatchConfig = None):
        self._connections: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # channel -> connection_ids
        self._connection_channels: Dict[str, Set[str]] = defaultdict(set)  # connection_id -> channels
        self._batcher = MessageBatcher(batch_config)
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, connection_id: str) -> bool:
        """Accept and register a WebSocket connection"""
        try:
            await websocket.accept()
            async with self._lock:
                self._connections[connection_id] = websocket
            logger.info(f"WebSocket connected: {connection_id}")
            return True
        except Exception as e:
            logger.error(f"WebSocket connect error: {e}")
            return False
    
    async def disconnect(self, connection_id: str):
        """Disconnect and cleanup a WebSocket connection"""
        async with self._lock:
            # Remove from connections
            self._connections.pop(connection_id, None)
            
            # Remove from all subscriptions
            channels = self._connection_channels.pop(connection_id, set())
            for channel in channels:
                self._subscriptions[channel].discard(connection_id)
            
            # Clear pending messages
            await self._batcher.clear(connection_id)
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, channel: str):
        """Subscribe a connection to a channel"""
        async with self._lock:
            self._subscriptions[channel].add(connection_id)
            self._connection_channels[connection_id].add(channel)
        logger.debug(f"Connection {connection_id} subscribed to {channel}")
    
    async def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe a connection from a channel"""
        async with self._lock:
            self._subscriptions[channel].discard(connection_id)
            self._connection_channels[connection_id].discard(channel)
    
    async def send_to_connection(
        self,
        connection_id: str,
        message_type: str,
        data: Any,
        priority: int = 0
    ):
        """Send message to a specific connection (batched)"""
        if connection_id not in self._connections:
            return
        
        websocket = self._connections[connection_id]
        
        async def flush_callback(batch: List[Dict]):
            await self._send_batch(websocket, batch)
        
        batch = await self._batcher.add_message(
            connection_id,
            message_type,
            data,
            priority,
            flush_callback
        )
        
        if batch:
            await self._send_batch(websocket, batch)
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message_type: str,
        data: Any,
        priority: int = 0
    ):
        """Broadcast message to all connections in a channel"""
        connection_ids = self._subscriptions.get(channel, set()).copy()
        
        for conn_id in connection_ids:
            await self.send_to_connection(conn_id, message_type, data, priority)
    
    async def broadcast_all(
        self,
        message_type: str,
        data: Any,
        priority: int = 0
    ):
        """Broadcast message to all connections"""
        connection_ids = list(self._connections.keys())
        
        for conn_id in connection_ids:
            await self.send_to_connection(conn_id, message_type, data, priority)
    
    async def send_immediate(
        self,
        connection_id: str,
        message_type: str,
        data: Any
    ):
        """Send message immediately without batching"""
        if connection_id not in self._connections:
            return
        
        websocket = self._connections[connection_id]
        message = {"type": message_type, "data": data}
        
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Send error to {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def _send_batch(self, websocket: WebSocket, batch: List[Dict]):
        """Send batch of messages"""
        try:
            for message in batch:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Batch send error: {e}")
    
    async def flush_connection(self, connection_id: str):
        """Force flush pending messages for a connection"""
        if connection_id not in self._connections:
            return
        
        websocket = self._connections[connection_id]
        batch = await self._batcher.flush_all(connection_id)
        
        if batch:
            await self._send_batch(websocket, batch)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self._connections)
    
    def get_channel_count(self, channel: str) -> int:
        """Get number of connections in a channel"""
        return len(self._subscriptions.get(channel, set()))


# Global WebSocket manager
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager(BatchConfig(
            max_batch_size=50,
            max_batch_delay_ms=100,
            enabled=True
        ))
    return _ws_manager


# ===== JSON Patch Helpers for Task Updates =====

def create_task_patch(task_id: str, field: str, value: Any) -> Dict:
    """Create a JSON patch for a task field update"""
    return {
        "op": "replace",
        "path": f"/tasks/{task_id}/{field}",
        "value": value
    }


def create_task_add_patch(task: Dict) -> Dict:
    """Create a JSON patch for adding a new task"""
    return {
        "op": "add",
        "path": f"/tasks/{task['id']}",
        "value": task
    }


def create_task_remove_patch(task_id: str) -> Dict:
    """Create a JSON patch for removing a task"""
    return {
        "op": "remove",
        "path": f"/tasks/{task_id}"
    }


async def broadcast_task_update(
    task_id: str,
    updates: Dict[str, Any],
    channel: str = "tasks"
):
    """Broadcast task update to all subscribers"""
    manager = get_websocket_manager()
    
    patches = [
        create_task_patch(task_id, field, value)
        for field, value in updates.items()
    ]
    
    await manager.broadcast_to_channel(
        channel,
        MessageType.PATCH,
        {"patches": patches}
    )


async def broadcast_task_created(task: Dict, channel: str = "tasks"):
    """Broadcast new task creation"""
    manager = get_websocket_manager()
    
    await manager.broadcast_to_channel(
        channel,
        MessageType.PATCH,
        {"patches": [create_task_add_patch(task)]},
        priority=1  # High priority, flush immediately
    )


async def broadcast_task_deleted(task_id: str, channel: str = "tasks"):
    """Broadcast task deletion"""
    manager = get_websocket_manager()
    
    await manager.broadcast_to_channel(
        channel,
        MessageType.PATCH,
        {"patches": [create_task_remove_patch(task_id)]},
        priority=1  # High priority, flush immediately
    )

