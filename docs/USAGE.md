# Usage Guide

This document provides detailed instructions for using the Smart Data Pipeline.

## Installation

### Prerequisites
- Python 3.10 or higher
- API keys for:
  - Ollama Cloud or OpenAI (for LLM capabilities)
  - Firecrawl (for web scraping)

### Setup Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   
   Create a `.env` file in the project root:
   ```bash
   cat > .env << EOF
   OLLAMA_API_KEY=your-ollama-api-key
   FIRECRAWL_API_KEY=your-firecrawl-api-key
   EOF
   ```

3. **Verify installation:**
   ```bash
   python -m src status
   ```

## CLI Commands

All commands use the format: `python -m src <command> [options]`

### Adding Data Sources

**Add a source to the queue:**
```bash
python -m src add "https://example.com/data"
```

**Add and process immediately:**
```bash
python -m src add "https://example.com/data" --now
```

This triggers the Scout → Builder workflow immediately instead of queuing the task.

### Monitoring

**Check pipeline status:**
```bash
python -m src status
```

Shows:
- Total number of sources
- Health breakdown (Active/Degraded/Quarantined/Dead)
- Individual source status with failure counts and last success time

**View task queue:**
```bash
python -m src tasks
```

Displays all pending, in-progress, and completed tasks with their state and target.

### Repairs

**Force repair of a specific source:**
```bash
python -m src fix <source_name>
```

This manually triggers the Doctor Agent to diagnose and patch the specified source, bypassing the automatic 3-failure threshold.

### Running the Orchestrator

**Start continuous orchestration:**
```bash
python -m src run
```

The orchestrator will:
- Process tasks from the queue
- Monitor source health
- Trigger automatic repairs when needed
- Run continuously until stopped (Ctrl+C)

**Process one task and exit:**
```bash
python -m src run --once
```

Useful for testing or cron jobs.

## Web Dashboard

**Launch the Streamlit dashboard:**
```bash
make ui
```

Or directly:
```bash
streamlit run src/ui/dashboard.py
```

Access at: `http://localhost:8501`

The dashboard provides:
- Real-time health monitoring
- Task queue visualization
- Fix history and audit logs
- Interactive charts and metrics

## REST API

**Start the API server:**
```bash
python run_server.py
```

Or with Docker:
```bash
docker-compose up --build
```

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Key Endpoints:**
- `POST /sources` — Add a new source
- `GET /sources` — List all sources
- `GET /sources/{name}` — Get source details
- `POST /sources/{name}/fix` — Trigger repair
- `GET /tasks` — View task queue

## Testing

**Run all tests:**
```bash
python -m pytest tests/ -v
```

**Run specific test suite:**
```bash
python -m pytest tests/test_end_to_end_agents.py -v
```

**Run with coverage:**
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## Configuration

All settings are in `src/core/config.py` and can be overridden with environment variables:

| Setting | Default | Environment Variable |
|---------|---------|---------------------|
| LLM Provider | `ollama` | `LLM_PROVIDER` |
| LLM Model | `gpt-oss:120b` | `LLM_MODEL` |
| LLM Timeout | `120s` | `LLM_TIMEOUT` |
| Database Path | `data/pipeline.db` | `PIPELINE_DB_PATH` |
| Max Fix Attempts | `3` per day | `MAX_FIX_ATTEMPTS` |
| Quarantine Threshold | `3` failures | `QUARANTINE_THRESHOLD` |

**Example: Use OpenAI instead of Ollama:**
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-openai-key
```

## Programmatic Usage

### Using the Orchestrator

```python
from src.orchestration import Orchestrator

# Initialize
orch = Orchestrator()

# Add a source
task = orch.add_source("https://example.com/data")

# Check status
status = orch.status()
print(f"Sources: {status['total_sources']}, Healthy: {status['healthy']}")

# Run orchestrator (blocking)
orch.run()
```

### Using Agents Directly

```python
from src.agents.scout import ScoutAgent
from src.agents.builder import BuilderAgent

# Scout analyzes a website
scout = ScoutAgent()
blueprint = scout.analyze("https://example.com/data")

# Builder generates code from blueprint
builder = BuilderAgent()
plugin_path = builder.build(blueprint)

print(f"Generated plugin: {plugin_path}")
```

### Accessing Storage Layers

```python
from src.storage.bronze import BronzeStorage
from src.storage.silver import SilverStorage

# Save to Bronze layer
bronze = BronzeStorage()
record_id = bronze.save(raw_data, source="my_source")

# Query Silver layer
silver = SilverStorage()
entities = silver.query(source="nba", type="game", limit=10)
```

## Troubleshooting

### Common Issues

**"No API key found for provider"**
- Ensure `OLLAMA_API_KEY` or `OPENAI_API_KEY` is set in `.env`
- Verify the file is in the project root directory

**Source stuck in QUARANTINED state**
- Wait 24 hours for automatic reset
- Or manually reset via database: `UPDATE source_health SET state='ACTIVE', failure_count=0 WHERE source_name='...'`

**Builder generates invalid code**
- Check the generated file in `src/registry/<source>.py`
- Review error logs for syntax issues
- Manually fix or delete the file and re-run `add` command

**Circuit breaker triggered**
- Max 3 fix attempts per day per source
- Wait for the daily reset or manually clear fix history in database

**Database locked errors**
- Ensure no other processes are accessing `data/pipeline.db`
- Close any SQLite browser tools
- Restart the orchestrator

### Logs and Debugging

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
python -m src run
```

**Check database directly:**
```bash
sqlite3 data/pipeline.db

# View task queue
SELECT * FROM task_queue ORDER BY created_at DESC LIMIT 10;

# View source health
SELECT * FROM source_health;

# View fix history
SELECT * FROM fix_history ORDER BY created_at DESC LIMIT 5;
```

## Workflow Examples

### Example 1: Adding a New Data Source

```bash
# Add the source
python -m src add "https://api.example.com/data" --now

# Monitor progress
python -m src status

# View the generated plugin
cat src/registry/example_data.py

# Check the data
sqlite3 data/pipeline.db "SELECT * FROM bronze_logs WHERE source='example_data';"
```

### Example 2: Monitoring and Repair

```bash
# Start the orchestrator in background
python -m src run &

# Watch the dashboard
make ui

# If a source fails, manually trigger repair
python -m src fix failing_source

# Check repair history
sqlite3 data/pipeline.db "SELECT * FROM fix_history WHERE source_name='failing_source';"
```

### Example 3: Batch Processing

```bash
# Add multiple sources
python -m src add "https://site1.com/data"
python -m src add "https://site2.com/data"
python -m src add "https://site3.com/data"

# Process all queued tasks
python -m src run --once

# Verify all succeeded
python -m src status
```
