import sys
from loguru import logger

# Remove default handler
logger.remove()

# Configure stdout handler (structured for production, colored for dev could be added via env var check)
# For now, following the plan: JSON structured logs are priority for stability/observability
# But for local dev friendliness, we might want a hybrid approach.
# The plan said: "Console: JSON formatted for production, colorized for dev."
# Let's keep it simple and user-friendly by default, but structured if we were in a strictly prod env.
# However, the user specifically asked for "Stability" and "Production Readiness".
# Let's add a serialized sink for file logging and a pretty sink for console.

# 1. Console Sink (Human Readable)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 2. File Sink (JSON Structured - mimicking production needs)
logger.add(
    "logs/pipeline.log",
    rotation="10 MB",
    retention="1 week",
    compression="zip",
    serialize=True,
    level="DEBUG"
)

# Export logger
__all__ = ["logger"]
