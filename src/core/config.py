"""
Centralized configuration for the Smart Data Pipeline.

All model, provider, and system settings in one place.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "ollama"  # "ollama" or "openai"
    model: str = "gpt-oss:120b"  # Default Ollama model
    base_url: str = "https://ollama.com"
    temperature: float = 0.0
    timeout_seconds: int = 120


@dataclass 
class PipelineConfig:
    """Pipeline behavior configuration."""
    db_path: str = "data/pipeline.db"
    registry_path: str = "src/registry"
    staging_path: str = "src/registry/staging"
    
    # Orchestrator settings
    poll_interval_seconds: int = 5
    stale_task_hours: int = 24
    
    # Health/Circuit breaker settings
    max_fix_attempts_per_day: int = 3
    quarantine_threshold: int = 3  # consecutive failures
    default_quarantine_hours: int = 24


@dataclass
class MCPConfig:
    """MCP tool server configuration."""
    firecrawl_enabled: bool = True


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment with defaults."""
    provider = os.getenv("LLM_PROVIDER", "auto")
    
    # Auto-detect based on available keys
    if provider == "auto":
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        else:
            # Default to Ollama if no explicit OpenAI key found
            # This supports local users without any keys set
            provider = "ollama"
    
    if provider == "ollama":
        return LLMConfig(
            provider="ollama",
            model=os.getenv("LLM_MODEL", "gpt-oss:120b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "https://ollama.com"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT", "120")),
        )
    else:
        return LLMConfig(
            provider="openai",
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT", "60")),
        )


def get_pipeline_config() -> PipelineConfig:
    """Get pipeline configuration from environment with defaults."""
    return PipelineConfig(
        db_path=os.getenv("PIPELINE_DB_PATH", "data/pipeline.db"),
        registry_path=os.getenv("REGISTRY_PATH", "src/registry"),
        staging_path=os.getenv("STAGING_PATH", "src/registry/staging"),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL", "5")),
        stale_task_hours=int(os.getenv("STALE_TASK_HOURS", "24")),
        max_fix_attempts_per_day=int(os.getenv("MAX_FIX_ATTEMPTS", "3")),
        quarantine_threshold=int(os.getenv("QUARANTINE_THRESHOLD", "3")),
        default_quarantine_hours=int(os.getenv("QUARANTINE_HOURS", "24")),
    )


# Singleton instances
_llm_config: Optional[LLMConfig] = None
_pipeline_config: Optional[PipelineConfig] = None


def llm_config() -> LLMConfig:
    """Get cached LLM config."""
    global _llm_config
    if _llm_config is None:
        _llm_config = get_llm_config()
    return _llm_config


def pipeline_config() -> PipelineConfig:
    """Get cached pipeline config."""
    global _pipeline_config
    if _pipeline_config is None:
        _pipeline_config = get_pipeline_config()
    return _pipeline_config
