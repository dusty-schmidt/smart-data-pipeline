# Silver Layer Architecture

> **Status**: Stable (Phase 1.3 Complete)
> **Philosophy**: Domain Agnostic, Traceable, and Idempotent.
> **Automation**: Populated by manual parsers and **Agent-built** plugins.

## Overview

The **Silver Layer** is the "Refinery" of the pipeline. It takes raw JSON blobs from the Bronze Layer and transforms them into structured, queryable entities. 

Crucially, this layer is designed to be **Domain Agnostic**. Instead of having separate tables for `Games`, `Stocks`, and `Weather`, we use a single distinct `SilverEntity` table with a flexible schema.

## The Silver Entity (`silver_entities`)

### Schema

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER (PK)` | Auto-incrementing internal ID. |
| `source` | `STRING` | The provider (e.g., `nba`, `alpaca`, `gov_weather`). |
| `type` | `STRING` | The object type (e.g., `game`, `quote`, `user`). |
| `external_id` | `STRING` | The ID in the remote system (e.g., `game_001`). |
| `timestamp` | `DATETIME` | When the event occurred (searchable). |
| `status` | `STRING` | Current state (e.g., `Final`, `Active`). |
| `name` | `STRING` | Human-readable title (e.g., `Lakers vs Celtics`). |
| `labels` | `JSON` | **New**: Arbitrary tagging (e.g., `{"season": "2024", "sport": "nba"}`). |
| `data` | `JSON` | The core domain-specific payload (scores, prices, etc.). |

### Key Features

1.  **Idempotency (Upsert Logic)**:
    *   Uniqueness is enforced by the composite key `(source, type, external_id)`.
    *   If you save an entity that already exists, it **updates** the existing record (Status, Timestamp, Data, Labels) instead of creating a duplicate.
    
2.  **Custom Labeling**:
    *   The `labels` column allows the AI or user to tag entities with domain-specific metadata without changing the database schema.
    *   Example: Tagging a game with `{"confidence": "high"}` or a stock with `{"sector": "tech"}`.

3.  **Domain Agnostic**:
    *   The same table holds NBA games and Stock Market quotes.
    *   Queries can filter by `labels` or `data` using JSON functions if needed, but the high-level metadata (Time, Status, Name) is always indexed for fast access.

## Usage

### Upserting Data

```python
from src.storage.silver import SilverStorage

storage = SilverStorage()

entity = {
    "source": "nba",
    "type": "game",
    "external_id": "game_123",
    "timestamp": datetime.now(),
    "status": "Final",
    "name": "Lakers vs Celtics",
    "labels": {"season": "2024", "league": "NBA"},
    "data": {"home_score": 102, "away_score": 99}
}

# Automatically decides to Insert or Update
storage.upsert_entity(entity)
```
