# Architecture

This document describes the core architectural patterns of the Smart Data Pipeline.

## Storage Layers

### Bronze Layer
The Bronze layer stores data **exactly as received** from the internet. No validation, cleaning, or modification occurs at this stage, ensuring we can always replay history if parsing logic changes.

**Technology:** SQLite via SQLAlchemy

**Schema:** `bronze_logs` table with columns: `id`, `source`, `ingested_at`, `version`, `payload` (JSON)

**Why SQLite?**
- Single `.db` file easier to manage than thousands of JSON files
- SQL queryability for debugging and analysis
- ACID transactions prevent data corruption
- Forward compatible: migrating to PostgreSQL is a one-line change

### Silver Layer
The Silver layer is the "refinery" that transforms raw JSON into structured, queryable entities. It's **domain agnostic** - a single `silver_entities` table holds NBA games, stock quotes, and any other data type.

**Schema:** `silver_entities` table with columns: `id`, `source`, `type`, `external_id`, `timestamp`, `status`, `name`, `labels` (JSON), `data` (JSON)

**Key Features:**
- **Idempotent upserts**: Composite key `(source, type, external_id)` prevents duplicates
- **Flexible labeling**: Tag entities with arbitrary metadata without schema changes
- **Domain agnostic**: Same table structure for all data types

## Parser Contract

All parsers inherit from `BaseParser` and implement a single method:

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        pass
```

**ParsingResult** is a data transfer object with fields: `external_id`, `type`, `data`, `labels`

This contract ensures that regardless of input format (XML, JSON, CSV), the output is always a standardized list of entities ready for the Silver layer.

## Dynamic Plugin System

The plugin registry enables hot-loading of new code without system restart. This is how AI agents can generate, test, and deploy new scrapers in real-time.

**How it works:**
1. Builder Agent generates a new parser and saves it to `src/registry/`
2. Plugin registry scans the directory for `.py` files
3. Dynamically imports modules using Python's `importlib`
4. Inspects for classes inheriting from `BaseParser`
5. Registers them for immediate use

**Staging:** Patches from the Doctor Agent are deployed to `src/registry/staging/` for validation before promotion to production.

## MCP Integration

The MCP (Model Context Protocol) Manager provides AI agents with access to external tools like web scraping and browser automation.

**Capabilities:**
- Add/remove tool servers at runtime
- Call tools with structured parameters
- Persist configuration to `config/mcp.json`

This allows agents to "install" new capabilities as needed without code changes.
