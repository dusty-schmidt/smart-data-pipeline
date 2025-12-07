# Setup and Utility Scripts

This directory contains one-time setup scripts and utility tools for the project.

## Scripts

### `register_firecrawl.py`
Registers the Firecrawl MCP server in `config/mcp.json`.

**When to run:**
- Once during initial project setup
- After changing `FIRECRAWL_API_KEY` in `.env`
- If you need to re-register the MCP server

**Usage:**
```bash
python3 scripts/register_firecrawl.py
```

**What it does:**
1. Loads `FIRECRAWL_API_KEY` from `.env`
2. Registers the `firecrawl-mcp` server with `MCPManager`
3. Saves configuration to `config/mcp.json`

## Future Scripts

This directory can contain:
- Database initialization scripts
- Migration tools
- Development utilities
- Deployment helpers
