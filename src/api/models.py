from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

class SourceCreate(BaseModel):
    url: str
    priority: int = 5

class SourceResponse(BaseModel):
    name: str
    state: str
    last_success: Optional[datetime] = None
    failures: int
    
class SourceHealth(BaseModel):
    active: int
    degraded: int
    quarantined: int
    dead: int

class SystemStatus(BaseModel):
    pending_tasks: int
    total_sources: int
    healthy: int
    degraded: int
    quarantined: int
    dead: int
    sources: List[SourceResponse]

class TaskResponse(BaseModel):
    task_id: int
    type: str
    state: str
    target: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]

class GenericResponse(BaseModel):
    message: str
    data: Optional[Any] = None
