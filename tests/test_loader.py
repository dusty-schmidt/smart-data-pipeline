from datetime import datetime
from src.core.plugins import PluginRegistry
from loguru import logger
import sys

def test_dynamic_loading():
    logger.info("Testing Dynamic Plugin Loading...")
    
    # 1. Initialize Registry
    registry = PluginRegistry()
    registry.discover_parsers()
    
    # 2. Verify we found the NBA plugin (which we moved to src/registry/nba_plugin.py)
    if "NBAScoreboardParser" not in registry.parsers:
        logger.error("Failed to discover NBAScoreboardParser!")
        sys.exit(1)
        
    logger.info("Successfully discovered NBAScoreboardParser.")
    
    # 3. Instantiate and Use
    parser = registry.get_parser("NBAScoreboardParser")
    
    # Mock Data
    mock_payload = {
        "payload": {
            "scoreboard": {
                "games": [{"gameId": "999", "homeTeam": {"teamTricode": "TST", "score": 0}, "awayTeam": {"teamTricode": "TST2", "score": 0}}]
            }
        }
    }
    
    results = parser.parse(mock_payload)
    assert len(results) == 1
    assert results[0].source == "nba"
    
    logger.success("Verification Passed: Dynamic Loading functional.")

    logger.success("Verification Passed: Dynamic Loading functional.")

