"""
Database configuration and models with proper indexing
Uses SQLAlchemy async for performance
"""

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Index, Enum,
    create_engine, event
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
from typing import Optional, List
import enum
import os

# Database URL - Use SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vivify.db")

# For SQLite, enable WAL mode for better concurrent performance
SQLITE_PRAGMA = {
    "journal_mode": "WAL",
    "cache_size": -64000,  # 64MB cache
    "synchronous": "NORMAL",
    "temp_store": "MEMORY",
    "mmap_size": 268435456,  # 256MB mmap
}

Base = declarative_base()


class TaskStatusEnum(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "inprogress"
    IN_REVIEW = "inreview"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskModel(Base):
    """Task model with optimized indexes for common queries"""
    __tablename__ = "tasks"
    
    id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=TaskStatusEnum.TODO.value)
    priority = Column(String(20), nullable=True)
    assignee = Column(String(100), nullable=True)
    project_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    task_metadata = Column(JSON, nullable=True)
    
    # Relationships
    subtasks = relationship("SubtaskModel", back_populates="task", cascade="all, delete-orphan")
    
    # Indexes for common query patterns
    __table_args__ = (
        # Index for filtering by status (most common query)
        Index('idx_tasks_status', 'status'),
        # Index for filtering by project
        Index('idx_tasks_project_id', 'project_id'),
        # Composite index for status + project (common filter combination)
        Index('idx_tasks_project_status', 'project_id', 'status'),
        # Index for sorting by updated_at (common for "recent tasks")
        Index('idx_tasks_updated_at', 'updated_at'),
        # Index for sorting by created_at
        Index('idx_tasks_created_at', 'created_at'),
        # Composite index for project + updated_at (recent tasks in project)
        Index('idx_tasks_project_updated', 'project_id', 'updated_at'),
        # Index for assignee filtering
        Index('idx_tasks_assignee', 'assignee'),
        # Index for priority filtering
        Index('idx_tasks_priority', 'priority'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "subtasks": [s.to_dict() for s in self.subtasks] if self.subtasks else [],
            "metadata": self.task_metadata or {}
        }


class SubtaskModel(Base):
    """Subtask model"""
    __tablename__ = "subtasks"
    
    id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    task_id = Column(String(50), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("TaskModel", back_populates="subtasks")
    
    # Indexes
    __table_args__ = (
        # Index for task_id (foreign key queries)
        Index('idx_subtasks_task_id', 'task_id'),
        # Composite index for task + status
        Index('idx_subtasks_task_status', 'task_id', 'status'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "task_id": self.task_id,
        }


class GCPResourceCacheModel(Base):
    """Cache table for GCP resources with indexes"""
    __tablename__ = "gcp_resource_cache"
    
    id = Column(String(100), primary_key=True)
    project_id = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    region = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    data = Column(JSON, nullable=False)  # Full resource JSON
    cached_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        # Index for project queries
        Index('idx_gcp_cache_project', 'project_id'),
        # Index for resource type queries
        Index('idx_gcp_cache_type', 'resource_type'),
        # Composite index for project + type (common filter)
        Index('idx_gcp_cache_project_type', 'project_id', 'resource_type'),
        # Index for region filtering
        Index('idx_gcp_cache_region', 'region'),
        # Index for expiry checking
        Index('idx_gcp_cache_expires', 'expires_at'),
        # Composite for project + region
        Index('idx_gcp_cache_project_region', 'project_id', 'region'),
    )


# Engine and session factory
_engine = None
_async_session_factory = None


async def init_database():
    """Initialize database and create tables"""
    global _engine, _async_session_factory
    
    _engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DEBUG", "false").lower() == "true",
        pool_pre_ping=True,
    )
    
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Enable SQLite optimizations if using SQLite
        if "sqlite" in DATABASE_URL:
            for pragma, value in SQLITE_PRAGMA.items():
                await conn.execute(f"PRAGMA {pragma} = {value}")
    
    print("✅ Database initialized with optimized indexes")


async def get_session() -> AsyncSession:
    """Get database session"""
    if _async_session_factory is None:
        await init_database()
    return _async_session_factory()


async def close_database():
    """Close database connection"""
    global _engine
    if _engine:
        await _engine.dispose()

