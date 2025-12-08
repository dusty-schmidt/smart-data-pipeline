---
description: Running the project's test suite
---

This workflow describes how to run the automated tests for the project.

1. Ensure you have dependencies installed:
   ```bash
   uv pip install -r requirements.txt
   ```

2. Run the tests using the Makefile:
// turbo
   ```bash
   make test
   ```
   
   Or manually with uv:
   ```bash
   uv run pytest tests/ -v
   ```

The test suite includes:
- **Unit Tests**: For individual components like parsers and load logic.
- **Integration Tests**: `test_end_to_end_agents.py` checks the agent workflow.
- **API Tests**: `test_api.py` checks the FastAPI endpoints.
- **Scout Tests**: `test_scout.py` performs a live check against a public URL (Internet required).
