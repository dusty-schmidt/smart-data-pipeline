# Contributing Guide

Guide for human contributors and ruleset for LLM agent coders.

## Core Principles

**Separation of Concerns**
- `src/agents/` — AI workers (analyze, build, repair)
- `src/orchestration/` — Task management, health tracking
- `src/storage/` — Bronze/Silver data layers
- `src/core/` — Infrastructure (config, LLM, MCP, plugins)
- `src/api/` — FastAPI routes and models

**Contract-Based Design**
- All parsers inherit `BaseParser` and implement `parse()` → `List[ParsingResult]`
- All fetchers inherit `BaseFetcher` and implement `fetch()`

**Fail Gracefully**
- Single source failures don't crash the orchestrator
- LLM unavailability doesn't prevent system operation
- Database errors are caught and logged

**Persistent State**
- Task queue, source health, and fix history stored in database
- System survives restarts and resumes work

## Development Practices

**1. Use UV Package Manager**
```bash
uv pip install -r requirements.txt
uv pip install <package>
```

**2. Document Your Work**
- Create markdown files in `dev-docs/` with problem, alternatives, approach, gotchas
- Example: `dev-docs/2025-12-07-doctor-agent-refactor.md`

**3. Proper File Organization**
- Scripts → `scripts/`
- Tests → `tests/`
- Dev docs → `dev-docs/`
- **Never** create `test.py`, `debug.py`, `temp_script.py` at project root

**4. No File Proliferation**
- Don't create `test_api.py`, `testing_api.py`, `debug_api.py`, `api_test_final.py`
- Work within one file, delete old attempts before creating new ones

**5. No Hardcoded Variables**
- All config in `src/core/config.py`, overridable via environment variables
- Bad: `timeout = 30`
- Good: `timeout = Config().llm_timeout`

**6. Root Cause Debugging**
- Fix underlying issues, not symptoms
- No band-aid fixes or whack-a-mole debugging
- Example: Fix connection pooling, not retry loops for database locks

**7. Minimal Code Changes**
- Change only what's necessary
- Don't refactor unrelated code in same commit
- One logical change per commit

## Code Style

**Python**
- Type hints on all function signatures
- PEP 8 naming, max 100 chars/line
- Docstrings for public methods

**Imports**
```python
# Standard library
import os

# Third-party
from sqlalchemy import create_engine

# Local
from src.core.config import Config
```

**Error Handling**
```python
# Good
try:
    result = fetch_data(url)
except requests.HTTPError as e:
    logger.error(f"HTTP error fetching {url}: {e}")
    raise FetchError(f"Failed to fetch {url}") from e

# Bad
try:
    result = fetch_data(url)
except:
    pass
```

## Testing

**Requirements**
- Run `python -m pytest tests/ -v` before submitting
- Add tests for new functionality
- Unit tests: `tests/test_<module>.py`
- Integration: `tests/test_end_to_end_*.py`

## Adding Features

**New Agent**
1. Create in `src/agents/`, inherit `BaseAgent`
2. Add tests in `tests/test_<agent>.py`
3. Update `ARCHITECTURE.md` if core patterns change

**New Parser**
1. Create in `src/registry/`, inherit `BaseParser`
2. Implement `parse()` → `List[ParsingResult]`

**New API Endpoint**
1. Add route in `src/api/routes.py`
2. Add models in `src/api/models.py`
3. Update `docs/API.md`
4. Add test in `tests/test_api.py`

## Git Workflow

**Branches**
- `main` — Production-ready
- `feature/<name>` — New features
- `fix/<name>` — Bug fixes

**Commits**
```
feat: add Scout analysis capability
fix: correct Bronze storage timestamp
docs: update ARCHITECTURE.md
test: add Doctor agent integration test
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## LLM Agent Rules

1. **Inherit from base classes** — `BaseParser`, `BaseFetcher`, `BaseAgent`
2. **Use type hints** — All function signatures
3. **Handle errors explicitly** — No bare `except:`
4. **Return structured data** — `ParsingResult`, `DataBlueprint`, etc.
5. **Log important events** — `logger.info()`, `logger.error()`
6. **Keep it simple** — Clarity over cleverness
7. **Test assumptions** — Add validation checks

**Parser Template**
```python
from src.processing.base import BaseParser, ParsingResult
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MyParser(BaseParser):
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        try:
            items = message.get("items", [])
            return [
                ParsingResult(
                    external_id=item["id"],
                    type="my_type",
                    data={"field": item["value"]},
                    labels={"source": "my_source"}
                ) for item in items
            ]
        except KeyError as e:
            logger.error(f"Missing field: {e}")
            return []
```

## Reference

- `docs/ARCHITECTURE.md` — Architectural decisions
- `docs/USAGE.md` — Usage examples
- `README.md`, `VISION.md` — Project vision

