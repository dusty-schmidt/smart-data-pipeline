import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables explicitly
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import threading

from src.orchestration.orchestrator import Orchestrator
from src.api.routes import router
from src.core.config import get_pipeline_config

# Global orchestrator instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    logger.info("Initializing API and Orchestrator...")
    
    # Initialize Orchestrator
    orchestrator = Orchestrator()
    orchestrator.startup()
    
    # Start Orchestrator loop in a separate thread to not block API
    # We use a thread because the Orchestrator loop is blocking (while True...)
    # In a fully async system, we'd rewrite Orchestrator to be async.
    orchestrator_thread = threading.Thread(target=orchestrator.run, daemon=True)
    orchestrator_thread.start()
    
    yield
    
    logger.info("Shutting down Orchestrator...")
    orchestrator.stop()
    # Wait for thread to finish (optional, but good practice)
    orchestrator_thread.join(timeout=5.0)

def create_app() -> FastAPI:
    app = FastAPI(
        title=os.getenv("PROJECT_NAME", "Smart Data Pipeline API"),
        description=os.getenv("PROJECT_DESCRIPTION", "Adaptive Ingestion Engine API"),
        version="1.0.0",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router)
    
    return app

# Entry point for uvicorn
app = create_app()
