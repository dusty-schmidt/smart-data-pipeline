from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict

from src.orchestration.orchestrator import Orchestrator
from src.api.models import (
    SourceCreate, SourceResponse, SystemStatus, TaskResponse, GenericResponse
)

router = APIRouter()

# Dependency to get orchestrator instance
# In a real app, this might be a singleton dependency
def get_orchestrator():
    # We will rely on the app state being set up in main.py
    # or import a singleton if defined in a global scope
    from src.api.app import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orchestrator

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/status", response_model=SystemStatus)
def get_system_status(orch: Orchestrator = Depends(get_orchestrator)):
    return orch.status()

@router.post("/sources", response_model=GenericResponse)
def add_source(
    source: SourceCreate, 
    background_tasks: BackgroundTasks,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """Add a new source to be discovered."""
    task = orch.add_source(source.url, source.priority)
    return GenericResponse(
        message=f"Source queued for discovery",
        data={"task_id": task.task_id}
    )

@router.get("/sources", response_model=List[SourceResponse])
def list_sources(orch: Orchestrator = Depends(get_orchestrator)):
    status = orch.status()
    return status["sources"]

@router.post("/sources/{name}/fix", response_model=GenericResponse)
def fix_source(name: str, orch: Orchestrator = Depends(get_orchestrator)):
    """Force a fix for a specific source."""
    # Check if source exists (simple check via status)
    status = orch.status()
    sources = [s["name"] for s in status["sources"]]
    if name not in sources:
        raise HTTPException(status_code=404, detail=f"Source '{name}' not found")
        
    task = orch.fix_source(name)
    return GenericResponse(
        message=f"Fix queued for source '{name}'",
        data={"task_id": task.task_id}
    )

@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(orch: Orchestrator = Depends(get_orchestrator)):
    # We need to expose a method in Orchestrator to get recent tasks
    # For now, we'll access the task_queue directly if possible, or add a method
    # Since Orchestrator wraps task_queue, let's just peek into it safely
    # Ideally Orchestrator should expose `get_recent_tasks()`
    
    # Accessing internal task_queue for MVP (Thread safety warning: minimal risk for SQLite read)
    # TODO: Add get_all_tasks to Orchestrator public API
    tasks = orch.task_queue.get_all_tasks(limit=50) 
    
    return [
        TaskResponse(
            task_id=t.task_id,
            type=t.task_type.value,
            state=t.state.value,
            target=t.target,
            created_at=t.created_at,
            started_at=t.started_at,
            completed_at=t.completed_at,
            error=t.error_message
        ) for t in tasks
    ]
