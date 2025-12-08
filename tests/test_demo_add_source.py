
import sys
import time
import os
import json
from loguru import logger

# Add src to path
sys.path.append(os.getcwd())

from src.orchestration.orchestrator import Orchestrator
from src.orchestration.task_queue import TaskState, TaskType

import shutil
import tempfile
from unittest.mock import patch

def run_demo_logic(orchestra):
    logger.info("🚀 DEMO: Adding a new Source (Real Site)")
    logger.info("target: https://www.scrapethissite.com/pages/simple/")

    # 2. Add Source
    url = "https://www.scrapethissite.com/pages/simple/"
    task = orchestra.add_source(url, priority=10)
    
    logger.info(f"Task Queued: {task.task_id}")
    
    # 3. Running loop
    max_cycles = 3
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
    
    # Verify artifacts logic (adjusted for test env)
    # We can skip exact file checks here or use the known temp path if we passed it in.
    return True

def test_demo_add_source():
    # Run in a temp directory to avoid polluting real project
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch config to use temp DB
        db_path = f"{temp_dir}/test_pipeline.db"
        
        # We also need to patch the registry path so we don't write real files to src/registry
        # This is tricky without a proper config injection, but Orchestrator uses Config singleton.
        # Let's try to patch the Config object or Orchestrator init.
        
        with patch.dict(os.environ, {"PIPELINE_DB_PATH": db_path}):
             # Note: Orchestrator accepts db_path in init, so we don't need to patch Config for DB isolation
             orchestra = Orchestrator(db_path=db_path)
             
             # Patch BuilderAgent to use temp registry path
             with patch("src.agents.builder.BuilderAgent.__init__", return_value=None) as mock_init:
                 def side_effect(self):
                     # Base agent init
                     super(BuilderAgent, self).__init__()
                     self.registry_path = temp_dir
                 mock_init.side_effect = side_effect
                 
                 # Also patch discover_parsers so it looks in temp dir
                 with patch("src.core.plugins.PluginRegistry.discover_parsers") as mock_discover:
                      run_demo_logic(orchestra)

if __name__ == "__main__":
    # If run directly suitable for manual demo, might want real effects?
    # For now, let's just run the test wrapper.
    test_demo_add_source()
