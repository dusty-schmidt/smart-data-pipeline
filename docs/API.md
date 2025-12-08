# API Reference

The REST API is accessible at `http://localhost:8000` with interactive documentation at `/docs` (Swagger) and `/redoc`.

## Endpoints

### Health Check
- **GET** `/health` — System health check

### System Status
- **GET** `/status` — Get pipeline status, source health, and metrics

### Sources
- **POST** `/sources` — Add a new data source
- **GET** `/sources` — List all sources
- **POST** `/sources/{name}/fix` — Trigger repair for a specific source

### Tasks
- **GET** `/tasks` — View task queue (up to 50 recent tasks)

## Authentication

_Not yet implemented. API is currently open._

## Rate Limiting

_Not yet implemented._

---

**Note:** This API is under active development. Endpoints and response formats may change.
