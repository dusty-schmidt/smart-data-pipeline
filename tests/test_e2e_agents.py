import sys
import os
import shutil
from unittest.mock import MagicMock
from loguru import logger
import unittest

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.agents.scout import ScoutAgent
from src.agents.builder import BuilderAgent
from src.agents.models import DataBlueprint
from src.ingestion.fetcher import BaseFetcher
from src.processing.base import BaseParser, ParsingResult

class TestAgentEndToEnd(unittest.TestCase):
    def setUp(self):
        self.registry_path = "src/registry"
        # CLEANUP: Remove ANY previous e2e_test_source.py to ensure fresh run
        if os.path.exists(os.path.join(self.registry_path, "e2e_test_source.py")):
            os.remove(os.path.join(self.registry_path, "e2e_test_source.py"))

    def tearDown(self):
        # Optional: Cleanup after test. Comment out to inspect generated file.
        if os.path.exists(os.path.join(self.registry_path, "e2e_test_source.py")):
            os.remove(os.path.join(self.registry_path, "e2e_test_source.py"))

    def test_agent_loop_mocked_llm(self):
        """
        Verifies that the BuilderAgent can take a Blueprint and write a valid Python file
        to the registry, even if the LLM content is mocked.
        """
        logger.info("Starting End-to-End Agent Loop Test (Mocked LLM)")

        # 1. Setup Agents
        builder = BuilderAgent()
        
        # Mock LLM because we don't have an API key in this environment.
        builder.llm = MagicMock()
        builder.llm.api_key = "dummy_key_for_test" # Mock check passes
        
        # The code the "LLM" would generate
        builder.llm.chat_completion.return_value = """
import httpx
from typing import Dict, Any, List
from src.ingestion.fetcher import BaseFetcher
from src.processing.base import BaseParser, ParsingResult

class E2ETestFetcher(BaseFetcher):
    def __init__(self):
        super().__init__("http://example.com")

class E2ETestParser(BaseParser):
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        return []
"""

        # 2. Simulate Scout Result (Blueprint)
        blueprint = DataBlueprint(
            source_name="e2e_test_source",
            base_url="http://example.com",
            description="A test source for E2E verification",
            fetch_strategy="http",
            root_selector="div.data"
        )
        
        # 3. Run Builder
        logger.info("Running Builder...")
        file_path = builder.build(blueprint)
        logger.info(f"Builder created file at: {file_path}")
            
        # 4. Verify Content
        self.assertTrue(os.path.exists(file_path), "File should be created")
        
        with open(file_path, "r") as f:
            content = f.read()
            
        self.assertIn("class E2ETestFetcher(BaseFetcher):", content)
        self.assertIn("class E2ETestParser(BaseParser):", content)
        logger.success("✅ Generated code verified.")

if __name__ == "__main__":
    unittest.main()
