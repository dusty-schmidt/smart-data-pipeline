"""
Task Queue - Persistent task management for Tier 2 Orchestration

Provides persistent task queue backed by SQLite.
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from enum import Enum

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from src.storage.models import Base, TaskRecord


class TaskType(Enum):
    ADD_SOURCE = "ADD_SOURCE"
    FIX_SOURCE = "FIX_SOURCE"
    REFRESH_SOURCE = "REFRESH_SOURCE"


class TaskState(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


@dataclass
class Task:
    """Represents a task in the queue."""
    task_id: Optional[int]
    task_type: TaskType
    target: str  # source_name or URL
    state: TaskState
    priority: int = 5
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @classmethod
    def from_record(cls, record: TaskRecord) -> "Task":
        """Convert SQLAlchemy record to Task dataclass."""
        return cls(
            task_id=record.id,
            task_type=TaskType(record.task_type),
            target=record.target,
            state=TaskState(record.state),
            priority=record.priority,
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            error_message=record.error_message,
            retry_count=record.retry_count,
            max_retries=record.max_retries,
        )


class TaskQueue:
    """
    Persistent task queue backed by SQLite.
    
    Survives restarts and allows resuming interrupted work.
    """
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}", 
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def add_task(self, task_type: TaskType, target: str, priority: int = 5) -> Task:
        """Add a new task to the queue."""
        session = self.Session()
        try:
            record = TaskRecord(
                task_type=task_type.value,
                target=target,
                state=TaskState.PENDING.value,
                priority=priority,
                created_at=datetime.now(timezone.utc),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"Task added: {task_type.value} → {target}")
            return Task.from_record(record)
        finally:
            session.close()
    
    def get_next_task(self) -> Optional[Task]:
        """
        Get highest priority pending task and mark as IN_PROGRESS.
        
        Returns None if queue is empty.
        """
        session = self.Session()
        try:
            record = (
                session.query(TaskRecord)
                .filter(TaskRecord.state == TaskState.PENDING.value)
                .order_by(TaskRecord.priority.desc(), TaskRecord.created_at.asc())
                .first()
            )
            if record is None:
                return None
            
            # Mark as in progress
            record.state = TaskState.IN_PROGRESS.value
            record.started_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            
            logger.info(f"Task claimed: [{record.id}] {record.task_type} → {record.target}")
            return Task.from_record(record)
        finally:
            session.close()
    
    def update_state(
        self, 
        task_id: int, 
        state: TaskState, 
        error: Optional[str] = None
    ) -> None:
        """Update task state with optional error message."""
        session = self.Session()
        try:
            record = session.query(TaskRecord).filter(TaskRecord.id == task_id).first()
            if record is None:
                logger.warning(f"Task {task_id} not found")
                return
            
            record.state = state.value
            if error:
                record.error_message = error
            if state in (TaskState.COMPLETED, TaskState.FAILED):
                record.completed_at = datetime.now(timezone.utc)
            if state == TaskState.FAILED:
                record.retry_count += 1
            
            session.commit()
            logger.info(f"Task [{task_id}] → {state.value}")
        finally:
            session.close()
    
    def get_in_progress_tasks(self) -> List[Task]:
        """Get all in-progress tasks (for resume after restart)."""
        session = self.Session()
        try:
            records = (
                session.query(TaskRecord)
                .filter(TaskRecord.state == TaskState.IN_PROGRESS.value)
                .all()
            )
            return [Task.from_record(r) for r in records]
        finally:
            session.close()
    
    def cleanup_stale_tasks(self, max_age_hours: int = 24) -> int:
        """
        Mark old in-progress tasks as failed.
        
        Returns count of tasks cleaned up.
        """
        session = self.Session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            stale = (
                session.query(TaskRecord)
                .filter(
                    TaskRecord.state == TaskState.IN_PROGRESS.value,
                    TaskRecord.started_at < cutoff
                )
                .all()
            )
            
            count = 0
            for record in stale:
                record.state = TaskState.FAILED.value
                record.error_message = f"Stale task (started > {max_age_hours}h ago)"
                record.completed_at = datetime.now(timezone.utc)
                count += 1
            
            session.commit()
            if count > 0:
                logger.warning(f"Cleaned up {count} stale tasks")
            return count
        finally:
            session.close()
    
    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        session = self.Session()
        try:
            return session.query(TaskRecord).filter(
                TaskRecord.state == TaskState.PENDING.value
            ).count()
        finally:
            session.close()
    
    def get_all_tasks(self, limit: int = 50) -> List[Task]:
        """Get recent tasks for dashboard display."""
        session = self.Session()
        try:
            records = (
                session.query(TaskRecord)
                .order_by(TaskRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [Task.from_record(r) for r in records]
        finally:
            session.close()
