
import uvicorn
from loguru import logger
import os
import sys

# Add src to pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    logger.info("Starting Smart Data Pipeline API Server...")
    uvicorn.run(
        "src.api.app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True  # useful for dev
    )
