# Internal Documentation

This directory contains internal documentation for tools, integrations, and system knowledge that the AI agents use.

## Structure

### `/tools/`
Documentation for external tools and services integrated into the system:
- **firecrawl.md** - Firecrawl MCP server for web scraping
- **ollama.md** - Ollama Cloud LLM integration

### Purpose
This documentation serves multiple purposes:
1. **Human Reference** - Quick lookup for developers
2. **Agent Context** - AI agents can reference these docs when making decisions
3. **Knowledge Base** - Centralized information about capabilities and configurations

## Adding New Documentation
When integrating a new tool or capability:
1. Create a new `.md` file in the appropriate subdirectory
2. Include:
   - Overview
   - Setup/Configuration
   - Usage examples
   - API reference (if applicable)
   - Troubleshooting
3. Update this README with a link

## Related
- Main project documentation: `/docs/`
- Vision and roadmap: `/VISION.md`
- Status reports: `/docs/status_report_*.md`
