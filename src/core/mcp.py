"""
MCP (Model Context Protocol) Management

Provides:
- MCPManager: Configuration management for MCP servers (mcp.json)
- SimpleMCPClient: Synchronous interface for calling MCP tools
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPManager:
    """
    Manages the MCP Server configuration file.
    Allows the system to self-install or remove tool sources at runtime.
    """
    
    def __init__(self, config_path: str = "config/mcp.json"):
        self.config_path = Path(config_path)
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_config({"mcpServers": {}})

    def _read_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read MCP config: {e}")
            return {"mcpServers": {}}

    def _write_config(self, config: Dict[str, Any]):
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write MCP config: {e}")
            raise

    def list_servers(self) -> Dict[str, Any]:
        """Returns the dictionary of configured servers."""
        config = self._read_config()
        return config.get("mcpServers", {})

    def add_server(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> None:
        """Installs a new MCP server."""
        config = self._read_config()
        servers = config.get("mcpServers", {})
        
        server_config = {
            "command": command,
            "args": args
        }
        if env:
            server_config["env"] = env
            
        servers[name] = server_config
        config["mcpServers"] = servers
        
        self._write_config(config)
        logger.info(f"Installed MCP Server: {name}")

    def remove_server(self, name: str) -> None:
        """Removes an MCP server configuration."""
        config = self._read_config()
        servers = config.get("mcpServers", {})
        
        if name in servers:
            del servers[name]
            config["mcpServers"] = servers
            self._write_config(config)
            logger.info(f"Removed MCP Server: {name}")
        else:
            logger.warning(f"Attempted to remove non-existent server: {name}")


class SimpleMCPClient:
    """
    A synchronous client for interacting with MCP servers.
    Manages the async event loop internally for simpler integration.
    """
    
    def __init__(self):
        self.manager = MCPManager()
        
    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """
        Connects to the specified MCP server and executes a tool.
        
        Args:
            server_name: Name of the MCP server (from mcp.json)
            tool_name: Name of the tool to call
            arguments: Tool arguments as dict
            
        Returns:
            Tool execution result (parsed if possible)
        """
        if arguments is None:
            arguments = {}
            
        # 1. Get Server Config
        servers = self.manager.list_servers()
        if server_name not in servers:
            raise ValueError(f"MCP Server '{server_name}' not configured.")
            
        config = servers[server_name]
        command = config["command"]
        args = config["args"]
        env = os.environ.copy()
        if "env" in config:
            env.update(config["env"])
            
        # 2. Run Sync Wrapper
        try:
            result = asyncio.run(self._run_tool(command, args, env, tool_name, arguments))
            return self._parse_result(result)
        except Exception as e:
            logger.error(f"MCP Tool execution failed: {e}")
            logger.debug(f"Server: {server_name}, Tool: {tool_name}, Args: {arguments}")
            raise

    async def _run_tool(self, command: str, args: list, env: dict, tool_name: str, arguments: dict):
        """Internal async method to execute MCP tool."""
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return result

    def _parse_result(self, result: Any) -> Any:
        """
        Parse MCP result into usable format.
        Handles various result types from different MCP servers.
        """
        # Direct dict with expected keys
        if isinstance(result, dict):
            # Firecrawl-style: {"markdown": "..."} or {"links": [...]}
            if "markdown" in result:
                return result["markdown"]
            return result
        
        # String result
        if isinstance(result, str):
            return result
        
        # List of content items (common MCP pattern)
        if isinstance(result, list) and len(result) > 0:
            first = result[0]
            # MCP Content object with .text attribute
            if hasattr(first, 'text'):
                return first.text
            # Dict with 'text' key
            if isinstance(first, dict) and 'text' in first:
                return first['text']
            return result
        
        # Fallback
        return result
