import os
import sys
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from src.agents.scout import ScoutAgent
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Configure simple logging to stdout
logger.remove()
logger.add(sys.stdout, level="INFO")

def test_scout_integration():
    print("Initializing Scout Agent...")
    agent = ScoutAgent()
    
    url = "https://example.com"
    print(f"Analyzing {url}...")
    
    # We expect this to try Firecrawl. 
    # If API key is missing, it should log a warning and fallback to HTTPX.
    # If API key is present, it should succeed.
    try:
        blueprint = agent.analyze("Test Source", url)
        print("\n--- Blueprint Generated ---")
        print(blueprint.model_dump_json(indent=2))
        print("---------------------------")
        
        # Simple assertions
        assert blueprint.source_name == "Test Source"
        assert blueprint.base_url == url
        print("✅ Test Passed: Blueprint generated successfully.")
        
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scout_integration()
