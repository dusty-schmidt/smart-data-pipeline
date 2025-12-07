# Parsing Architecture

> **Status**: Stable (Phase 1.4 Complete)
> **Principle**: Strong Contracts for Generic Data.

## Overview

The transformation from "Bronze" (Raw) to "Silver" (Refined) is handled by **Parsers**. Because the upstream data sources change constantly, the parsing layer must be modular and strict.

We enforce a shared contract: `BaseParser`. This ensures that no matter what the input looks like (XML, JSON, CSV), the output is *always* a list of standard `ParsingResult` objects ready for the database.

> **Note**: As of Phase 2, most new parsers are written automatically by the **Builder Agent** (`src/agents/builder.py`) based on blueprints, ensuring they strictly adhere to this contract.

## The Contract (`src/processing/base.py`)

### `BaseParser`
The abstract base class that all specific parsers must inherit from.

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        pass
```

### `ParsingResult`
The data transfer object (DTO) that maps directly to the `silver_entities` table.

| Field | Description |
| :--- | :--- |
| `external_id` | Unique ID from the source (e.g. `game_001`). |
| `type` | The entity type (e.g. `game`, `stock`). |
| `data` | Cleaned dictionary payload. |
| `labels` | Metadata tags (e.g. `{"league": "nba"}`). |

## Workflow

1.  **Input**: The pipeline reads a generic JSON envelope from the Bronze Layer.
2.  **Transform**: The specific parser (e.g. `NBAScoreboardParser`) extracts relevant fields.
3.  **Output**: It returns a list of `ParsingResult` objects.
4.  **Load**: The pipeline passes these objects to `SilverStorage` for upserting.

## Example Implementation

```python
class NBAScoreboardParser(BaseParser):
    def parse(self, message):
        # ... logic to extract data ...
        return [
            ParsingResult(
                source="nba",
                type="game",
                external_id="001",
                data={"score": 100},
                labels={"league": "NBA"}
            )
        ]
```
