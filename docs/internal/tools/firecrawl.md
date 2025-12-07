# Firecrawl MCP Server

## Overview
Firecrawl is a web scraping tool that handles JavaScript-heavy sites and provides clean markdown output. We use it via the Model Context Protocol (MCP).

## Setup

### 1. Set API Key
```bash
# In .env file
FIRECRAWL_API_KEY=fc-your-key-here
```

### 2. Register Server
```bash
python3 scripts/register_firecrawl.py
```

## Available Tools

### firecrawl_scrape
Scrapes a single URL and returns markdown content.

```python
result = mcp.call_tool("firecrawl", "firecrawl_scrape", {
    "url": "https://example.com",
    "formats": ["markdown"],
    "onlyMainContent": True,
    "waitFor": 1000
})
```

### firecrawl_map
Discovers all URLs on a website.

```python
result = mcp.call_tool("firecrawl", "firecrawl_map", {
    "url": "https://example.com",
    "limit": 50,
    "ignoreQueryParameters": True
})
```

### firecrawl_search
Web search with optional scraping.

### firecrawl_batch_scrape
Batch scrape multiple URLs.

## Usage in Scout Agent

```python
from src.agents.scout import ScoutAgent

# Basic analysis
scout = ScoutAgent()
blueprint = scout.analyze("my_source", "https://example.com")

# With URL discovery
blueprint = scout.analyze("my_source", "https://example.com", discover_mode=True)
```

## Direct MCP Usage

```python
from src.core.mcp import SimpleMCPClient

mcp = SimpleMCPClient()

# Scrape
content = mcp.call_tool("firecrawl", "firecrawl_scrape", {
    "url": "https://example.com",
    "formats": ["markdown"]
})

# Map
urls = mcp.call_tool("firecrawl", "firecrawl_map", {
    "url": "https://example.com",
    "limit": 20
})
```

## Troubleshooting
- **API key error**: Ensure `FIRECRAWL_API_KEY` is in `.env`
- **Server fails**: Check that `npx` and Node.js are installed
- **Timeouts**: Increase `waitFor` parameter
