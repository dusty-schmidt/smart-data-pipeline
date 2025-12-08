"""
Orchestrator - Main coordination loop for Tier 2 Autonomy

Processes task queue, coordinates agents, and manages the pipeline lifecycle.
"""
import time
import sys
import inspect
from typing import Optional
from datetime import datetime

from loguru import logger

from src.orchestration.task_queue import TaskQueue, TaskType, TaskState, Task
from src.orchestration.health import HealthTracker, SourceState
from src.orchestration.doctor import DoctorAgent
from src.agents.scout import ScoutAgent
from src.agents.builder import BuilderAgent
from src.core.plugins import PluginRegistry
from src.storage.bronze import BronzeStorage
from src.storage.silver import SilverStorage


class Orchestrator:
    """
    Coordinates the full pipeline workflow.
    
    Workflow:
    1. On startup: resume/cleanup interrupted tasks
    2. Main loop: process task queue
       - ADD_SOURCE: Scout → Builder → Deploy
       - FIX_SOURCE: Doctor → Staging → Validate → Promote
       - REFRESH_SOURCE: Run scraper → Store in Bronze
    3. Monitor health → queue FIX_SOURCE tasks for degraded sources
    """
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = db_path
        self.task_queue = TaskQueue(db_path)
        self.health_tracker = HealthTracker(db_path)
        self.doctor = DoctorAgent(db_path)
        self.scout = ScoutAgent()
        self.builder = BuilderAgent()
        self.plugin_registry = PluginRegistry()
        
        # Storage classes expect a full SQLAlchemy URL
        db_url = f"sqlite:///{db_path}"
        self.bronze = BronzeStorage(db_url)
        self.silver = SilverStorage(db_url)
        
        # Configuration
        self.poll_interval_seconds = 5
        self.running = False
    
    def startup(self) -> None:
        """
        Startup routine: clean up stale tasks and resume interrupted work.
        """
        logger.info("[Orchestrator] Starting up...")
        
        # Clean up tasks that were in progress when we crashed
        stale_count = self.task_queue.cleanup_stale_tasks(max_age_hours=24)
        if stale_count > 0:
            logger.warning(f"[Orchestrator] Cleaned up {stale_count} stale tasks")
        
        # Check for interrupted tasks and reset them to PENDING
        in_progress = self.task_queue.get_in_progress_tasks()
        for task in in_progress:
            logger.warning(f"[Orchestrator] Resetting interrupted task: [{task.task_id}] {task.task_type.value}")
            self.task_queue.update_state(task.task_id, TaskState.PENDING)
        
        # Reload plugins
        self.plugin_registry.discover_parsers()
        
        logger.info("[Orchestrator] Startup complete")
    
    def add_source(self, url: str, priority: int = 5) -> Task:
        """
        Add a new data source to be discovered and built.
        """
        task = self.task_queue.add_task(TaskType.ADD_SOURCE, url, priority)
        logger.info(f"[Orchestrator] Queued ADD_SOURCE: {url}")
        return task
    
    def fix_source(self, source_name: str, priority: int = 8) -> Task:
        """
        Queue a repair task for a source.
        """
        task = self.task_queue.add_task(TaskType.FIX_SOURCE, source_name, priority)
        logger.info(f"[Orchestrator] Queued FIX_SOURCE: {source_name}")
        return task
    
    def refresh_source(self, source_name: str, priority: int = 3) -> Task:
        """
        Queue a refresh/scrape task for a source.
        """
        task = self.task_queue.add_task(TaskType.REFRESH_SOURCE, source_name, priority)
        logger.info(f"[Orchestrator] Queued REFRESH_SOURCE: {source_name}")
        return task
    
    def process_task(self, task: Task) -> bool:
        """
        Process a single task based on its type.
        
        Returns True if task completed successfully.
        """
        logger.info(f"[Orchestrator] Processing [{task.task_id}] {task.task_type.value} → {task.target}")
        
        try:
            if task.task_type == TaskType.ADD_SOURCE:
                return self._handle_add_source(task)
            elif task.task_type == TaskType.FIX_SOURCE:
                return self._handle_fix_source(task)
            elif task.task_type == TaskType.REFRESH_SOURCE:
                return self._handle_refresh_source(task)
            else:
                logger.error(f"[Orchestrator] Unknown task type: {task.task_type}")
                return False
                
        except Exception as e:
            logger.exception(f"[Orchestrator] Task failed: {e}")
            self.task_queue.update_state(task.task_id, TaskState.FAILED, str(e))
            return False
    
    def _handle_add_source(self, task: Task) -> bool:
        """
        Handle ADD_SOURCE: Scout analyzes URL → Builder generates code.
        """
        url = task.target
        
        # 1. Scout analyzes the URL
        logger.info(f"[Orchestrator] Scout analyzing: {url}")
        try:
            blueprint = self.scout.analyze(url)
        except Exception as e:
            logger.error(f"[Orchestrator] Scout failed: {e}")
            self.task_queue.update_state(task.task_id, TaskState.FAILED, f"Scout failed: {e}")
            return False
        
        logger.info(f"[Orchestrator] Blueprint created: {blueprint.source_name}")
        
        # 2. Builder generates code
        logger.info(f"[Orchestrator] Builder constructing: {blueprint.source_name}")
        try:
            file_path = self.builder.build(blueprint)
        except Exception as e:
            logger.error(f"[Orchestrator] Builder failed: {e}")
            self.task_queue.update_state(task.task_id, TaskState.FAILED, f"Builder failed: {e}")
            return False
        
        logger.info(f"[Orchestrator] Plugin created: {file_path}")
        
        # 3. Register in health tracker
        self.health_tracker.record_success(blueprint.source_name)
        
        # 4. Reload plugins
        self.plugin_registry.discover_parsers()
        
        # Success!
        self.task_queue.update_state(task.task_id, TaskState.COMPLETED)
        logger.success(f"[Orchestrator] Source deployed: {blueprint.source_name}")
        
        # Trigger immediate refresh
        self.refresh_source(blueprint.source_name, priority=10)
        
        return True
    
    def _handle_fix_source(self, task: Task) -> bool:
        """
        Handle FIX_SOURCE: Doctor heals the source.
        """
        source_name = task.target
        
        # Get current error from health tracker
        health = self.health_tracker.get_health(source_name)
        if health is None:
            logger.error(f"[Orchestrator] No health record for {source_name}")
            self.task_queue.update_state(task.task_id, TaskState.FAILED, "No health record")
            return False
        
        # Create a synthetic error from the last known error
        error = Exception(health.last_error or "Unknown error")
        
        # Run Doctor healing workflow
        success = self.doctor.heal(source_name, error)
        
        if success:
            self.task_queue.update_state(task.task_id, TaskState.COMPLETED)
            # Reload plugins after fix
            self.plugin_registry.discover_parsers()
            return True
        else:
            self.task_queue.update_state(task.task_id, TaskState.FAILED, "Doctor healing failed")
            return False
    
    def _handle_refresh_source(self, task: Task) -> bool:
        """
        Handle REFRESH_SOURCE: Run the scraper and store data.
        """
        source_name = task.target
        
        # Find the parser in the registry
        self.plugin_registry.discover_parsers()
        
        # Look for a matching parser class (case-insensitive)
        # Iterate over all registered parsers to find a match
        ParserClass = None
        target_name = f"{source_name}Parser".lower().replace("_", "").replace(" ", "")
        
        for name, cls in self.plugin_registry.parsers.items():
            current_name = name.lower().replace("_", "")
            if current_name == target_name:
                ParserClass = cls
                break
        
        try:
            if not ParserClass:
                logger.error(f"[Orchestrator] Parser class {parser_name} not found")
                self.task_queue.update_state(task.task_id, TaskState.FAILED, f"Parser class {parser_name} not found")
                return False

            # 1. Instantiate Plugin
            # We assume the plugin has a Fetcher class named {source}Fetcher
            # But the current PluginRegistry mainly handles Parsers.
            # To simplify, we will let the Parser/Plugin file handle fetching too if possible,
            # OR we standardize that the file contains both.
            # 
            # Given the current `src/registry/en_wikipedia_org.py`, it has `en_wikipedia_orgFetcher` and `en_wikipedia_orgParser`.
            # We need to reflectively find the Fetcher class too.
            
            # Re-import the module to get the Fetcher
            module = sys.modules[ParserClass.__module__]
            
            # Find fetcher class in the module (case-insensitive match)
            FetcherClass = None
            target_fetcher = f"{source_name}Fetcher".lower().replace("_", "")
            
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name.lower().replace("_", "") == target_fetcher:
                    FetcherClass = obj
                    break
            
            if not FetcherClass:
                 # Fallback: Maybe the module IS the fetcher/parser combo?
                 # For now, let's error if strictly missing.
                 logger.error(f"[Orchestrator] Fetcher class {fetcher_class_name} not found in {module}")
                 self.task_queue.update_state(task.task_id, TaskState.FAILED, "Fetcher not found")
                 return False

            fetcher = FetcherClass()
            parser = ParserClass()
            
            # 2. Fetch Data
            logger.info(f"[Orchestrator] Fetching data for {source_name}...")
            raw_data = fetcher.fetch()
            
            # 3. Store in Bronze
            bronze_id = self.bronze.save(raw_data, source_name)
            
            # 4. Parse
            logger.info(f"[Orchestrator] Parsing data (Bronze ID: {bronze_id})...")
            # Enriched data for parser if needed, but usually parser takes what fetcher returns
            parsing_results = parser.parse(raw_data)
            logger.info(f"[Orchestrator] Extracted {len(parsing_results)} entities")
            
            # 5. Store in Silver
            count = 0
            for item in parsing_results:
                self.silver.upsert_entity(item.to_dict())
                count += 1
                
            logger.success(f"[Orchestrator] Upserted {count} entities to Silver")
            
            # 6. Success
            self.task_queue.update_state(task.task_id, TaskState.COMPLETED)
            self.health_tracker.record_success(source_name)
            return True

        except Exception as e:
            logger.exception(f"[Orchestrator] Refresh failed: {e}")
            self.task_queue.update_state(task.task_id, TaskState.FAILED, str(e))
            return False
    
    def check_health_and_queue_fixes(self) -> int:
        """
        Check for degraded sources and queue fix tasks.
        
        Returns count of fix tasks queued.
        """
        degraded = self.health_tracker.get_degraded_sources()
        queued = 0
        
        for health in degraded:
            if health.state == SourceState.QUARANTINED:
                # Check if still quarantined
                if self.health_tracker.is_quarantined(health.source_name):
                    continue  # Still in timeout
            
            # Check if we can attempt a fix
            if not self.health_tracker.can_attempt_fix(health.source_name):
                continue  # Circuit breaker
            
            # Queue a fix task
            self.fix_source(health.source_name)
            queued += 1
        
        if queued > 0:
            logger.info(f"[Orchestrator] Queued {queued} fix tasks")
        
        return queued
    
    def process_queue(self) -> Optional[Task]:
        """
        Process one task from the queue.
        
        Returns the processed task or None if queue is empty.
        """
        task = self.task_queue.get_next_task()
        if task is None:
            return None
        
        self.process_task(task)
        return task
    
    def run(self, once: bool = False) -> None:
        """
        Main orchestration loop.
        
        Args:
            once: If True, process one task and exit (for testing)
        """
        self.startup()
        self.running = True
        
        logger.info("[Orchestrator] Starting main loop")
        
        while self.running:
            # Check for degraded sources and queue fixes
            self.check_health_and_queue_fixes()
            
            # Process one task
            task = self.process_queue()
            
            if task:
                if once:
                    break
            else:
                if once:
                    logger.info("[Orchestrator] Queue empty (once mode)")
                    break
                # Queue is empty, sleep before next poll
                logger.debug(f"[Orchestrator] Queue empty, sleeping {self.poll_interval_seconds}s")
                time.sleep(self.poll_interval_seconds)
        
        logger.info("[Orchestrator] Stopped")
    
    def stop(self) -> None:
        """Signal the orchestrator to stop."""
        self.running = False
        logger.info("[Orchestrator] Stop requested")
    
    def status(self) -> dict:
        """
        Get current status summary.
        """
        pending = self.task_queue.get_pending_count()
        sources = self.health_tracker.get_all_sources()
        
        return {
            "pending_tasks": pending,
            "total_sources": len(sources),
            "healthy": sum(1 for s in sources if s.state == SourceState.ACTIVE),
            "degraded": sum(1 for s in sources if s.state == SourceState.DEGRADED),
            "quarantined": sum(1 for s in sources if s.state == SourceState.QUARANTINED),
            "dead": sum(1 for s in sources if s.state == SourceState.DEAD),
            "sources": [
                {
                    "name": s.source_name,
                    "state": s.state.value,
                    "last_success": s.last_success_at.isoformat() if s.last_success_at else None,
                    "failures": s.consecutive_failures,
                }
                for s in sources
            ]
        }
