import httpx
import json
from bs4 import BeautifulSoup
from typing import Optional
from loguru import logger
from src.agents.base import BaseAgent
from src.agents.models import DataBlueprint


class ScoutAgent(BaseAgent):
    """
    The Analysis Agent.
    Role: Inspects a target URL and produces a 'Blueprint' for data extraction.
    """
    
    def __init__(self, user_agent: str = "Mozilla/5.0"):
        super().__init__()
        self.headers = {"User-Agent": user_agent}

    def analyze(self, source_name: str, url: str, discover_mode: bool = False) -> DataBlueprint:
        """
        Analyzes the page and attempts to auto-detect data structures.
        Tries Firecrawl MCP first, then falls back to basic HTTP fetching.
        
        Args:
            source_name: Name for this data source
            url: URL to analyze
            discover_mode: If True, uses firecrawl_map to discover related URLs first
        """
        logger.info(f"Scout is analyzing {url}...")
        
        content = None
        discovered_urls = []
        
        # 0. Optional: Discover related URLs using firecrawl_map
        if discover_mode:
            try:
                logger.info("Using Firecrawl map to discover URLs...")
                map_result = self.mcp.call_tool("firecrawl", "firecrawl_map", {
                    "url": url,
                    "limit": 20,
                    "ignoreQueryParameters": True
                })
                
                # Result is already parsed by SimpleMCPClient
                if isinstance(map_result, list):
                    discovered_urls = map_result[:10]
                elif isinstance(map_result, dict) and "links" in map_result:
                    discovered_urls = map_result["links"][:10]
                    
                if discovered_urls:
                    logger.info(f"Discovered {len(discovered_urls)} related URLs")
                    
            except Exception as e:
                logger.warning(f"Firecrawl map failed ({e}). Continuing with single URL.")
        
        # 1. Try Firecrawl scrape
        try:
            logger.info("Attempting Firecrawl scrape...")
            # SimpleMCPClient._parse_result() handles result extraction
            content = self.mcp.call_tool("firecrawl", "firecrawl_scrape", {
                "url": url, 
                "formats": ["markdown"],
                "onlyMainContent": True,
                "waitFor": 1000
            })
            
            # Ensure we have string content
            if content and isinstance(content, str):
                logger.info("Firecrawl scrape successful.")
        except Exception as e:
            logger.warning(f"Firecrawl failed ({e}). Falling back to HTTPX.")

        # 2. Fallback to basic HTTP
        if not content:
            try:
                with httpx.Client(headers=self.headers, follow_redirects=True) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    html = resp.text

                # Pre-process (Slim down HTML to save tokens)
                soup = BeautifulSoup(html, "html.parser")
                # Remove scripts and styles
                for tag in soup(["script", "style", "svg", "noscript"]):
                    tag.decompose()
                
                content = str(soup)[:50000] # Hard truncate
            except Exception as e:
                logger.error(f"HTTP fetch failed: {e}")
                raise

        # 3. LLM Analysis
        try:
            blueprint = self._ask_llm(source_name, url, content, discovered_urls)
            return blueprint
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise

    def _ask_llm(self, source_name: str, url: str, html_snippet: str, discovered_urls: list = None) -> DataBlueprint:
        """
        Sends HTML to LLM and requests a JSON Blueprint.
        """
        if not self.llm.api_key:
            logger.warning("No LLM API Key found. Returning empty blueprint.")
            return DataBlueprint(
                source_name=source_name,
                base_url=url,
                description="LLM Key missing. Cannot analyze."
            )

        system_prompt = """
        You are an expert Web Scraper. Your goal is to analyze the provided HTML and generate a configuration Blueprint.
        
        Output JSON matching this schema:
        {
            "source_name": "string",
            "base_url": "string",
            "fetch_strategy": "http", 
            "root_selector": "Generic CSS selector for the item container (e.g. 'div.product' or 'tr')",
            "fields": {
                "field_name": "CSS selector relative to root"
            },
            "domain_labels": {"topic": "string"},
            "description": "Short description of what is being extracted"
        }
        
        Focus on the MAIN data table or list in the page.
        """
        
        user_message = f"""
        Source Name: {source_name}
        URL: {url}
        """
        
        if discovered_urls:
            user_message += f"""
        
        Related URLs discovered on this site:
        {chr(10).join(f'- {u}' for u in discovered_urls[:5])}
        
        Consider these URLs when determining the data structure and field names.
        """
        
        user_message += f"""
        
        HTML Snippet:
        {html_snippet}
        """
        
        response_text = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            json_mode=True
        )
        
        try:
            data = json.loads(response_text)
            # Ensure required fields are set if LLM missed them
            data["source_name"] = source_name
            data["base_url"] = url
            return DataBlueprint(**data)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise

