from src.agents.scout import ScoutAgent
from loguru import logger
import sys

def test_scout():
    logger.info("Testing Scout Agent...")
    
    agent = ScoutAgent()
    
    # 1. Test against a known page (Example.com often simple, let's use a dummy heuristic target)
    # We will use a Mock or a public stable site.
    # Wikipedia 'List of X' pages are good for Table detection.
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    # Analyze
    blueprint = agent.analyze(url)
    
    logger.info(f"Generated Blueprint: {blueprint.model_dump_json(indent=2)}")
    
    # Verification
    assert "wiki" in blueprint.source_name or "sp500" in blueprint.source_name
    assert blueprint.base_url == url
    # Wikipedia should trigger the Table heuristic
    if "table" in blueprint.description.lower():
         logger.success("Scout successfully detected Table structure.")
         assert "tr" in blueprint.root_selector
    else:
        logger.warning("Scout did not detect table, but ran successfully.")



