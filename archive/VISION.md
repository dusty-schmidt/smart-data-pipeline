# Project Vision: Adaptive Data Pipeline

## Overview
A **self-sustaining data ecosystem** where AI agents discover, ingest, and maintain data sources automatically.

**Core Metaphor:** A manufacturing plant where robots build and maintain other robots.

---

## Architecture (Kernel Tiers)

```
Tier 0: Storage (Bronze/Silver)        ✅ Complete
Tier 1: Agents (Scout/Builder)         ✅ Complete  
Tier 2: Autonomy (Doctor/Orchestrator) ✅ Complete
Tier 3: Intelligence (Learning)        📋 Future
Tier 4: Ecosystem (Multi-domain)       📋 Future
```

---

## Current Status

### ✅ Tier 0: Storage (Complete)
- Bronze Layer (raw JSON storage)
- Silver Layer (normalized entities)
- ELT pattern with traceability

### ✅ Tier 1: Agents (Complete)
- **BaseAgent** - Common LLM/MCP patterns
- **ScoutAgent** - Web analysis → DataBlueprint
- **BuilderAgent** - Blueprint → Python code
- **PluginRegistry** - Hot-load generated code

### ✅ Tier 2: Autonomy (Complete)
Full implementation in `src/orchestration/`:
- **TaskQueue** - Persistent SQLite-backed task management
- **HealthTracker** - 3-strikes quarantine, circuit breaker
- **DoctorAgent** - LLM-based diagnosis, patching, staging/validation
- **Orchestrator** - Coordinates Scout → Builder → Doctor workflow
- **CLI** - Full command-line interface

---

## MVP Checklist

### Core Infrastructure ✅
- [x] Bronze/Silver storage layers
- [x] LLM client (Ollama/OpenAI)
- [x] MCP client for tools
- [x] Firecrawl integration
- [x] BaseAgent pattern
- [x] ScoutAgent (web → blueprint)
- [x] BuilderAgent (blueprint → code)
- [x] PluginRegistry (hot-load)

### Tier 2: Autonomy ✅
- [x] **Database tables** for orchestration
  - [x] `task_queue` table
  - [x] `source_health` table
  - [x] `fix_history` table

- [x] **TaskQueue** - Persistent task management
  - [x] Add/get tasks
  - [x] State transitions (PENDING → IN_PROGRESS → DONE)
  - [x] Resume after restart

- [x] **HealthTracker** - Source monitoring
  - [x] Record success/failure
  - [x] Quarantine logic (3 strikes)
  - [x] Health state (ACTIVE/DEGRADED/QUARANTINED/DEAD)

- [x] **DoctorAgent** - Self-healing
  - [x] Context collection (error + code + HTML diff)
  - [x] LLM diagnosis
  - [x] Patch generation
  - [x] Staging deployment
  - [x] Validation before production

- [x] **Orchestrator** - Workflow coordination
  - [x] Process task queue
  - [x] Coordinate Scout → Builder → Doctor
  - [x] Main loop

- [x] **CLI** - User interface
  - [x] `add <url>` - Add new source
  - [x] `status` - Show health
  - [x] `fix <source>` - Force repair
  - [x] `run` - Start orchestrator
  - [x] `tasks` - View task queue

### MVP Success Criteria
- [x] Zero-touch: URL → working scraper (no manual steps)
- [x] Persistent: Survives restart
- [ ] Self-healing: 80%+ auto-fix rate (needs real-world testing)
- [x] Observable: Dashboard shows health (Phase 5)

---

## User Experience (MVP)

```bash
# Add a source
$ python -m src add "https://example.com/data"
✅ Task queued: [1] ADD_SOURCE → https://example.com/data

# Process immediately
$ python -m src add "https://example.com/data" --now
🚀 Processing immediately...
✅ Scout analyzing...
✅ Blueprint generated
✅ Code generated  
✅ Source deployed: example_data

# Check status
$ python -m src status
📊 Pipeline Status
==================================================
Pending Tasks: 0
Total Sources: 2

Health Summary:
  ✅ Active:      2
  ⚠️  Degraded:    0
  🔒 Quarantined: 0
  💀 Dead:        0

Sources:
  ✅ example_data    (failures: 0, last: 2025-12-07 04:15)
  ✅ nba_stats       (failures: 0, last: 2025-12-07 04:10)

# View task queue
$ python -m src tasks
📋 Task Queue
======================================================================
ID    Type            State        Target                        
----------------------------------------------------------------------
1     ADD_SOURCE      COMPLETED    https://example.com/data

# Force repair
$ python -m src fix example_data
🔧 Repair queued: [2] FIX_SOURCE → example_data

# Run orchestrator loop
$ python -m src run
🚀 Starting orchestrator...
   Press Ctrl+C to stop
```

---

## Design Principles

1. **Kernel Isolation** - Each tier is independent
2. **Graceful Degradation** - Lower tiers keep working if higher tiers fail
3. **80/20 Rule** - Focus on high-value features first
4. **Persistent State** - Survive restarts
5. **Circuit Breakers** - Prevent infinite loops (max 3 fix attempts/day)

---

## Configuration

All settings centralized in `src/core/config.py`:

| Setting | Default | Environment Variable |
|---------|---------|---------------------|
| LLM Provider | `ollama` | `LLM_PROVIDER` |
| LLM Model | `gpt-oss:120b` | `LLM_MODEL` |
| Database | `data/pipeline.db` | `PIPELINE_DB_PATH` |
| Max Fix Attempts | `3` per day | `MAX_FIX_ATTEMPTS` |
| Quarantine Threshold | `3` failures | `QUARANTINE_THRESHOLD` |

---

## Post-MVP Roadmap

### Phase 5: Polish (In Progress)
- [x] Streamlit dashboard with health monitoring
- [x] Task queue visualization  
- [x] Fix history audit log
- [ ] Add logging/alerting
- [ ] Battle testing with volatile sources (48h run)

### Tier 3: Intelligence Kernel (Next)

**Step 1: The Learner (Pattern Recognition)**
- **Concept:** When the Doctor successfully fixes a scraper, save the "before/after" diff to a `knowledge_base` table
- **Application:** When the Builder creates a new scraper for a similar site, inject relevant "lessons" into the LLM prompt
- **Example:** *"This site uses Tailwind's dynamic class names; use structure-based selectors instead."*

**Implementation:**
```python
class KnowledgeBase:
    def record_lesson(self, source_name: str, error_type: str, fix_diff: str, tags: List[str])
    def find_relevant_lessons(self, html_sample: str, limit: int = 3) -> List[Lesson]
```

**Step 2: The Validator (Data Quality)**
- **Concept:** "No Crash" ≠ "Good Data"
- **Upgrade:** Add schema validation to the Silver Layer
- **Logic:** If Scout promised `{"price": float}` but scraper returns `{"price": null}`, flag as "Silent Failure" and trigger Doctor

**Implementation:**
```python
class SchemaValidator:
    def validate_output(self, blueprint: DataBlueprint, result: Dict) -> ValidationResult
    def detect_silent_failure(self, source_name: str, recent_outputs: List[Dict]) -> bool
```

### Tier 4: Ecosystem Kernel (Future)
- Multi-domain support (finance, sports, news, etc.)
- Agent marketplace (share/import blueprints)
- Federation across instances
- Observability (Prometheus metrics, Grafana dashboards)