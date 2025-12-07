# Storage Architecture

> **Status**: Stable (Phase 1.1 Complete)
> **Technology**: SQLite (via SQLAlchemy)

## Overview

The storage layer is the backbone of the "ELT" philosophy. Its primary responsibility is the **Bronze Layer** (The Universal Inbox). 

We have moved from a file-based logging system to a **Relational Database (SQLite)** to ensure scalability, query capability, and easier management without the operational overhead of a full server (Postgres) at this stage.

## The Bronze Layer (`bronze_logs`)

The "Bronze" layer stores data *exactly* as it is received from the internet. We do not validate, clean, or modify the payload at this stage. This ensures we can always "replay" history if our parsing logic changes.

> **Note**: Our AI Agents (Scout & Builder) generate fetchers that strictly output to this layer, ensuring that even AI-gathered data is fully auditable.

### Schema

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER (PK)` | Auto-incrementing unique identifier. |
| `source` | `STRING` | The name of the data provider (e.g., `nba_scoreboard`). |
| `ingested_at` | `DATETIME` | UTC timestamp of when we saved the data. |
| `version` | `STRING` | Schema version of our envelope (default: "1.0"). |
| `payload` | `JSON` | The **entire** raw JSON response from the API. |

### Rationale (The 80/20 Rule)

Why SQLite instead of JSON files or PostgreSQL?

1.  **Vs. JSON Files**:
    *   **Single Artifact**: One `.db` file is easier to manage than 10,000 `.json` files.
    *   **Queryability**: We can use SQL to count records, find missing dates, or debug specific sources instantly.
    *   **Performance**: ACID transactions ensure we don't write half-files if the script crashes.

2.  **Vs. PostgreSQL (for now)**:
    *   **Zero Ops**: No Docker containers, no user management, no connection timeouts.
    *   **Forward Compatibility**: We use **SQLAlchemy**. Migrating to Postgres in the future is literally a 1-line change:
        *   *Current*: `create_engine("sqlite:///data/pipeline.db")`
        *   *Future*: `create_engine("postgresql://user:pass@localhost/db")`

## Usage

### Saving Data

```python
from src.storage.bronze import BronzeStorage

storage = BronzeStorage()
record_id = storage.save(raw_json_data, source="nba_scoreboard")
print(f"Saved to ID: {record_id}")
```

### Retrieving Data

```python
data = storage.get(record_id)
payload = data['payload']
metadata = data['metadata']
```
