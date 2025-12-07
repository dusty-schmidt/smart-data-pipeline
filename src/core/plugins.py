import importlib
import sys
import pkgutil
import inspect
from typing import Dict, Type, List
from pathlib import Path
from loguru import logger
from src.processing.base import BaseParser

class PluginRegistry:
    """
    Dynamically loads and registers parsers from the src/registry directory.
    This allows the AI to drop a new file into that folder, and the system 
    will pick it up immediately (or on next run).
    """
    
    def __init__(self, registry_dir: str = "src/registry"):
        self.registry_dir = registry_dir
        self.parsers: Dict[str, Type[BaseParser]] = {}

    def discover_parsers(self):
        """
        Scans the registry directory for Python modules.
        Imports them and looks for subclasses of BaseParser.
        """
        registry_path = Path(self.registry_dir)
        
        # Ensure it exists
        if not registry_path.exists():
            logger.warning(f"Registry directory {registry_path} does not exist.")
            return

        # 1. Add registry to sys.path so we can import modules
        # (Assuming run from root)
        package_name = self.registry_dir.replace("/", ".")
        
        logger.info(f"Scanning for plugins in {package_name}...")

        # Walk through modules in the directory
        for file_path in registry_path.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            
            module_name = f"{package_name}.{file_path.stem}"
            
            try:
                # Dynamic Import
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)
                
                # Inspect for BaseParser classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseParser) and 
                        obj is not BaseParser):
                        
                        # Register it
                        # Key could be specific, let's use class name for now
                        self.parsers[name] = obj
                        logger.info(f"Registered Plugin: {name}")
                        
            except Exception as e:
                logger.error(f"Failed to load plugin {module_name}: {e}")

    def get_parser(self, class_name: str) -> BaseParser:
        """Instantiates a parser dynamically"""
        if class_name not in self.parsers:
            raise ValueError(f"Parser {class_name} not found in registry.")
        return self.parsers[class_name]()
