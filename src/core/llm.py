import os
import httpx
import json
from typing import Dict, Any, Optional, List
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.config import llm_config, LLMConfig


class LLMClient:
    """
    A unified client for interacting with LLM APIs.
    Supports both OpenAI-compatible APIs and Ollama Cloud.
    
    Uses centralized config from src/core/config.py
    """
    def __init__(self, config: Optional[LLMConfig] = None):
        # Use provided config or get from centralized config
        cfg = config or llm_config()
        
        self.provider = cfg.provider
        self.model = cfg.model
        self.base_url = cfg.base_url
        self.temperature = cfg.temperature
        self.timeout = cfg.timeout_seconds
        self.use_ollama = cfg.provider == "ollama"
        
        # Get API key from environment
        if self.use_ollama:
            self.api_key = os.getenv("OLLAMA_API_KEY")
        else:
            self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key and not self.use_ollama:
            logger.warning(f"No API key found for provider '{self.provider}'. LLM features will fail if called.")
        elif self.use_ollama and not self.api_key:
             logger.info(f"LLM Client initialized: provider={self.provider} (No API Key required for local Ollama), model={self.model}")
        else:
            logger.info(f"LLM Client initialized: provider={self.provider}, model={self.model}")

    def chat_completion(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        """
        Sends a chat completion request to the LLM.
        Routes to Ollama or OpenAI-compatible API based on configuration.
        """
        if not self.api_key and not self.use_ollama:
            raise ValueError(f"API key not set for provider '{self.provider}'.")

        if self.use_ollama:
            # Ollama client has its own retry logic usually, but we could wrap this too if needed.
            # unique case for now: just wrap common network errors for HTTP logic
            return self._ollama_chat(messages, json_mode)
        else:
            return self._openai_chat(messages, json_mode)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception)), # Ideally narrowed down, but Ollama lib exceptions vary
        reraise=True
    )
    def _ollama_chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        """
        Uses the Ollama Python client for Ollama Cloud.
        """
        try:
            from ollama import Client
            
            client = Client(
                host=self.base_url,
                headers={'Authorization': f'Bearer {self.api_key}'}
            )
            
            # Ollama doesn't support json_mode in the same way, but we can request it in the prompt
            if json_mode and messages:
                last_msg = messages[-1]
                if last_msg.get("role") == "user":
                    last_msg["content"] += "\n\nPlease respond with valid JSON only."
            
            response = client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            return response['message']['content']
            
        except ImportError:
            logger.error("ollama library not installed. Run: pip install ollama")
            raise
        except Exception as e:
            logger.warning(f"Ollama request failed: {e}. Retrying...")
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        reraise=True
    )
    def _openai_chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        """
        Uses HTTP requests for OpenAI-compatible APIs.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            resp = httpx.post(url, headers=headers, json=payload, timeout=float(self.timeout))
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(f"OpenAI API connection issue: {e}. Retrying...")
            raise
        except Exception as e:
            logger.error(f"OpenAI-compatible API request failed: {e}")
            raise
