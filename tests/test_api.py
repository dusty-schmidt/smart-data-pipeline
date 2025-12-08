from fastapi.testclient import TestClient
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

import src.api.app as app_module
from src.api.app import app
from src.orchestration.orchestrator import Orchestrator

# Initialize orchestrator for tests
test_orchestrator = Orchestrator()
test_orchestrator.startup()

# Replace the global orchestrator instance in the app module
app_module.orchestrator = test_orchestrator

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_status():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_sources" in data
    assert "pending_tasks" in data

def test_add_source():
    # Attempt to add a dummy source
    source_payload = {
        "url": "https://example.com/test-data",
        "priority": 10
    }
    response = client.post("/sources", json=source_payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data["data"]
    
    # Verify it appears in tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    found = False
    for t in tasks:
        if t["target"] == "https://example.com/test-data":
            found = True
            break
    assert found
