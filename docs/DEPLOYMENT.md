# Deployment

## Docker

The system can be deployed using Docker Compose:

```bash
docker-compose up --build
```

This starts the FastAPI server on port 8000 with the orchestrator running in the background.

## Database

SQLite is used by default (`data/pipeline.db`). For production at scale, migrate to PostgreSQL by changing the connection string in `src/core/config.py`.

## Environment Variables

Required in production:
- `OLLAMA_API_KEY` or `OPENAI_API_KEY`
- `FIRECRAWL_API_KEY`

Optional:
- `LLM_PROVIDER` (default: `ollama`)
- `LLM_MODEL` (default: `gpt-oss:120b`)
- `PIPELINE_DB_PATH` (default: `data/pipeline.db`)
