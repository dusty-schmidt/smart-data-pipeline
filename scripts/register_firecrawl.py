import os
import sys

# Add project root to path so we can import from src/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.mcp import MCPManager

def register_firecrawl():
    m = MCPManager()
    
    # Load .env to get the API key
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("WARNING: FIRECRAWL_API_KEY not found in environment. Server may not work.")
        print("Please add FIRECRAWL_API_KEY to your .env file.")
    
    # Always pass the env var (even if empty) so the server can see it
    env_vars = {"FIRECRAWL_API_KEY": api_key} if api_key else {}

    m.add_server(
        name="firecrawl",
        command="npx",
        args=["-y", "firecrawl-mcp"],
        env=env_vars
    )
    
    if api_key:
        print("✅ Firecrawl server registered with API key.")
    else:
        print("⚠️  Firecrawl server registered WITHOUT API key (will fail at runtime).")

if __name__ == "__main__":
    register_firecrawl()
