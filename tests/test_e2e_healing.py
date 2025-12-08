
import unittest
import shutil
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
import sys
sys.path.append(os.getcwd())

from src.orchestration.orchestrator import Orchestrator
from src.orchestration.health import HealthTracker, SourceState
from src.orchestration.task_queue import TaskState
from src.storage.models import Lesson

class TestE2EHealing(unittest.TestCase):
    def setUp(self):
        # 1. Create temporary environment
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        
        # Setup paths
        self.db_path = self.root / "pipeline.db"
        self.registry_path = self.root / "src/registry"
        self.registry_path.mkdir(parents=True)
        
        # 2. Create a "broken" scraper
        self.source_name = "broken_site"
        self.scraper_file = self.registry_path / f"{self.source_name}.py"
        self.original_code = """
class BrokenSite:
    def parse(self, html):
        # This selector is wrong
        return html.find("div", class_="old-class").text
"""
        self.scraper_file.write_text(self.original_code)
        
        # 3. Initialize Orchestrator with temp paths
        # We need to monkey-patch the Doctor's registry path since it's hardcoded in __init__ usually
        with patch("src.orchestration.doctor.DoctorAgent.__init__", autospec=True) as mock_init:
            # We want the real init logic, but to override paths after
            def side_effect(self, db_path):
                # Call base class logic manually or just setup what we need
                # To invoke real super().__init__ is tricky with autospec, 
                # so we instantiate normally and then patch instances? 
                # Easier approach: Use patch.object on the instance properties
                pass
            
        self.orchestra = Orchestrator(db_path=str(self.db_path))
        
        # Override Doctor's paths to point to our temp dir
        self.orchestra.doctor.registry_path = self.registry_path
        self.orchestra.doctor.staging_path = self.root / "src/registry/staging"
        self.orchestra.doctor.staging_path.mkdir(parents=True)
        
        # 4. Inject meaningful mock LLM responses
        self.mock_llm_patcher = patch.object(self.orchestra.doctor, 'ask_llm')
        self.mock_llm = self.mock_llm_patcher.start()
        
        def mock_llm_response(prompt, **kwargs):
            if "Diagnose" in prompt or "DiagnosisContext" in prompt or "Error Context" in prompt:
                return json.dumps({
                    "root_cause": "The class 'old-class' no longer exists.",
                    "fix_strategy": "patch",
                    "suggested_fix": "Use 'new-class'",
                    "confidence": 0.99
                })
            elif "Apply the fix" in prompt or "Current Code" in prompt:
                return """
class BrokenSite:
    def parse(self, html):
        # PATCHED
        return html.find("div", class_="new-class").text
"""
            elif "generalized lesson" in prompt:
                return json.dumps({
                    "domain_pattern": "test_sites",
                    "symptom_description": "obsolete class",
                    "fix_strategy": "update class name",
                    "reasoning": "sites change"
                })
            return "{}"
            
        self.mock_llm.side_effect = mock_llm_response

    def tearDown(self):
        self.mock_llm_patcher.stop()
        self.test_dir.cleanup()

    def test_end_to_end_healing(self):
        """
        Scenario:
        1. Source fails enough times to be broken (DEGRADED).
        2. Orchestrator detects this and queues a FIX_SOURCE task.
        3. Orchestrator processes the task (Doctor heals it).
        4. Verify code is patched and lesson is learned.
        """
        print("\n🚀 Starting E2E Healing Test...")
        
        # 1. Simulate a degraded source
        tracker = self.orchestra.health_tracker
        # Record 2 failures to make it DEGRADED (assuming threshold is 2)
        tracker.record_failure(self.source_name, "ValueError: old-class not found")
        tracker.record_failure(self.source_name, "ValueError: old-class not found")
        
        health = tracker.get_health(self.source_name)
        self.assertIn(health.state, [SourceState.DEGRADED, SourceState.QUARANTINED])
        print("   ✅ Source marked as DEGRADED")
        
        # 2. Run Orchestrator loop (Health Check)
        # This should queue a FIX_SOURCE task
        queued_count = self.orchestra.check_health_and_queue_fixes()
        self.assertEqual(queued_count, 1)
        print("   ✅ Fix task queued")
        
        # Verify task is in queue
        all_tasks = self.orchestra.task_queue.get_all_tasks()
        task = next(t for t in all_tasks if t.state == TaskState.PENDING and t.target == self.source_name)
        self.assertEqual(task.target, self.source_name)
        
        # 3. Process the Task
        # We process manually to control execution flow
        print("   ... Doctor is operating ...")
        success = self.orchestra.process_task(task)
        self.assertTrue(success)
        print("   ✅ Task processed successfully")
        
        # 4. Verifications
        
        # A. File Content Changed
        new_code = self.scraper_file.read_text()
        self.assertIn('class_="new-class"', new_code)
        self.assertNotIn('class_="old-class"', new_code)
        print("   ✅ Code was successfully patched on disk")
        
        # B. Lesson Learned
        session = self.orchestra.doctor.Session()
        lessons = session.query(Lesson).all()
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0].fix_strategy, "update class name")
        session.close()
        print("   ✅ New lesson added to Knowledge Base")
        
        # C. Task State
        all_tasks_final = self.orchestra.task_queue.get_all_tasks()
        updated_task = next(t for t in all_tasks_final if t.task_id == task.task_id)
        self.assertEqual(updated_task.state, TaskState.COMPLETED)
        print("   ✅ Task marked COMPLETED")

if __name__ == '__main__':
    unittest.main()
