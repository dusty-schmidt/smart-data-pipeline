import os
from src.core.plugins import PluginRegistry
from loguru import logger
import unittest

class TestPluginLoading(unittest.TestCase):
    def setUp(self):
        self.registry_path = "src/registry"
        self.plugin_path = os.path.join(self.registry_path, "dummy_plugin.py")
        
        # Create a dummy plugin file
        with open(self.plugin_path, "w") as f:
            f.write("""
from typing import Dict, Any, List
from src.processing.base import BaseParser, ParsingResult

class DummyTestParser(BaseParser):
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        return [ParsingResult("test", "dummy", "1", {}, None)]
""")

    def tearDown(self):
        if os.path.exists(self.plugin_path):
            os.remove(self.plugin_path)

    def test_dynamic_loading(self):
        logger.info("Testing Dynamic Plugin Loading...")
        
        # 1. Initialize Registry
        registry = PluginRegistry()
        registry.discover_parsers()
        
        # 2. Verify we found the Dummy plugin
        if "DummyTestParser" not in registry.parsers:
             logger.error("Failed to discover DummyTestParser!")
             # Fail test
             assert False, "DummyTestParser not found"
            
        logger.info("Successfully discovered DummyTestParser.")
        
        # 3. Instantiate and Use
        parser = registry.get_parser("DummyTestParser")
        results = parser.parse({})
        
        assert len(results) == 1
        assert results[0].source == "test"
        
        logger.success("Verification Passed: Dynamic Loading functional.")


