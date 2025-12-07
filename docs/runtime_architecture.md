# Dynamic Runtime Architecture

> **Status**: Stable (Phase 2.0 Complete)
> **Principle**: Hot-Pluggable Logic.

## Overview

The core of the **Adaptive System** is the ability to load code without restarting the infrastructure. This allows the AI Agents to generate, test, and deploy new scrapers/parsers in real-time.

## The Plugin Registry (`src/core/plugins.py`)

This registry is heavily utilized by the **Builder Agent**. When the Builder generates a new source file, it places it into `src/registry/`, and this runtime immediately loads it, closing the loop.

We utilize a simple file-system based discovery mechanism.

1.  **Registry Directory**: `src/registry/`
2.  **Discovery**: The system scans this folder for `.py` files.
3.  **Loading**: It dynamically imports them using Python's `importlib`.
4.  **Registration**: It inspects the module for classes that inherit from `BaseParser`.

## Adding a New Parser (Manual or via AI)

To add support for a new domain (e.g., NFL), drop a file `src/registry/nfl_plugin.py`:

```python
from src.processing.base import BaseParser, ParsingResult

class NFLScoreboardParser(BaseParser):
    def parse(self, message):
        # ... logic ...
        return [ParsingResult(...)]
```

The system will automatically detect `NFLScoreboardParser` on the next scan.

## Security Note

For this phase, we run the code in the same process.
*   **Risk**: Malicious parser could crash the app or access globals.
*   **Mitigation (Future)**: Move parser execution to `subprocess` or Docker containers.

## The MCP Manager (`src/core/mcp.py`)

Manages **MCP Tools** for AI agents. Contains both `MCPManager` (config) and `SimpleMCPClient` (execution).

*   **Capabilities**: `add_server`, `remove_server`, `call_tool`
*   **Use Case**: AI can "install" new tools at runtime (e.g., Firecrawl, browser automation)
*   **Persistence**: Settings saved to `config/mcp.json`
