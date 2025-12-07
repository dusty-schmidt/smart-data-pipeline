"""
Base Agent - Common patterns for all AI agents.
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from src.core.llm import LLMClient
from src.core.mcp import SimpleMCPClient


class BaseAgent:
    """
    Base class for all AI agents in the system.
    
    Provides:
    - LLM client for chat completions
    - MCP client for tool execution
    - Common utility methods
    """
    
    def __init__(self):
        self.llm = LLMClient()
        self.mcp = SimpleMCPClient()
    
    def call_tool(self, server: str, tool: str, args: Dict[str, Any] = None) -> Any:
        """
        Execute an MCP tool.
        
        Args:
            server: MCP server name (e.g., "firecrawl")
            tool: Tool name (e.g., "firecrawl_scrape")
            args: Tool arguments
            
        Returns:
            Parsed tool result
        """
        return self.mcp.call_tool(server, tool, args or {})
    
    def ask_llm(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        json_mode: bool = False
    ) -> str:
        """
        Send a prompt to the LLM.
        
        Args:
            prompt: User message
            system_prompt: Optional system message
            json_mode: Request JSON response format
            
        Returns:
            LLM response text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.llm.chat_completion(messages, json_mode=json_mode)
    
    def ask_llm_with_messages(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False
    ) -> str:
        """
        Send full message history to LLM.
        
        Args:
            messages: List of {"role": ..., "content": ...} dicts
            json_mode: Request JSON response format
            
        Returns:
            LLM response text
        """
        return self.llm.chat_completion(messages, json_mode=json_mode)
