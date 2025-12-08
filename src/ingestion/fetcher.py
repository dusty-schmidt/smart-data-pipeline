import httpx
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class BaseFetcher:
    """
    The Golden Template for Data Ingestion.
    Implements robust error handling, retries, and standard headers.
    """
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, url: Optional[str] = None, timeout: int = 10, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.timeout = timeout
        self.headers = {**self.DEFAULT_HEADERS, **(headers or {})}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.ConnectError, httpx.TimeoutException)),
        reraise=True
    )
    def fetch(self) -> Dict[str, Any]:
        """
        Fetches data with automatic retries and error handling.
        """
        logger.info(f"Attempting to fetch data from: {self.url}")
        
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = client.get(self.url)
                
                # Raise for 4xx and 5xx
                response.raise_for_status()
                
                # Check if content type is JSON
                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type and not response.text.strip().startswith(("{", "[")):
                    logger.warning(f"Response might not be JSON. Content-Type: {content_type}")
                
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error {e.response.status_code} for {self.url}")
            raise
        except Exception as e:
            logger.error(f"Fetch failed for {self.url}: {str(e)}")
            raise
