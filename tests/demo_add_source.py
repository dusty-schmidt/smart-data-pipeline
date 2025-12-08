
import sys
import time
import os
import json
from loguru import logger

# Add src to path
sys.path.append(os.getcwd())

from src.orchestration.orchestrator import Orchestrator
from src.orchestration.task_queue import TaskState, TaskType

def demo_add_source():
    logger.info("🚀 DEMO: Adding a new Source (Real Site)")
    logger.info("target: https://www.scrapethissite.com/pages/simple/")
    
    # 1. Initialize Orchestrator
    orchestra = Orchestrator() # Uses real data/pipeline.db
    
    # 2. Add Source
    url = "https://www.scrapethissite.com/pages/simple/"
    task = orchestra.add_source(url, priority=10)
    
    logger.info(f"Task Queued: {task.task_id}")
    
    # 3. Running loop
    # We want to process:
    # 1. ADD_SOURCE (Scout -> Builder)
    # 2. auto-triggered REFRESH_SOURCE (Fetcher -> Parser -> Silver)
    
    max_cycles = 10
    cycle = 0
    
    # Start orchestrator
    orchestra.startup()
    
    while cycle < max_cycles:
        # Helper: Wait for task processing
        pass
        
        # Manually process one task
        processed = orchestra.process_queue()
        
        if processed:
             logger.info(f"Processed task: {processed.task_type} -> {processed.target} ({processed.state})")
             if processed.task_type == TaskType.ADD_SOURCE and processed.state == TaskState.COMPLETED:
                 logger.success("✅ ADD_SOURCE completed! Scout & Builder worked.")
             
             if processed.task_type == TaskType.REFRESH_SOURCE and processed.state == TaskState.COMPLETED:
                 logger.success("✅ REFRESH_SOURCE completed! Fetcher & Parser worked.")
                 break # Done!
        
        time.sleep(2)
        cycle += 1
        
    logger.info("🏁 Demo finished.")
    
    # Verify artifacts
    # 1. Check registry file
    registry_file = "src/registry/www_scrapethissite_com.py"
    if os.path.exists(registry_file):
        logger.success(f"File exists: {registry_file}")
    else:
        logger.error(f"File missing: {registry_file}")
        
    # 2. Check Bronze
    # Using raw SQL to check recent
    # (Assuming sqlite3 is available via orchestration)
    # But easier to just list dir
    bronze_files = os.listdir("data/bronze")
    if bronze_files:
        logger.success(f"Found {len(bronze_files)} files in data/bronze")
    else:
        logger.error("No data in bronze!")

if __name__ == "__main__":
    demo_add_source()
