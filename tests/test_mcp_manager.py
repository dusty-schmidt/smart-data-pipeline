import os
from src.core.mcp import MCPManager
from loguru import logger
import sys

def test_mcp_flow():
    logger.info("Testing Dynamic MCP Registry...")
    
    # 1. Initialize
    # Use a temp config for testing to allow concurrency if needed? 
    # For now, explicit test config path.
    TEST_CONFIG = "config/mcp_test.json"
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)
        
    manager = MCPManager(config_path=TEST_CONFIG)
    
    # 2. Add Server
    server_name = "test-fs"
    manager.add_server(
        name=server_name,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    )
    
    # 3. Verify List
    servers = manager.list_servers()
    assert server_name in servers
    assert servers[server_name]["command"] == "npx"
    logger.info("Verified: Server added successfully.")
    
    # 4. Remove Server
    manager.remove_server(server_name)
    
    # 5. Verify Removal
    servers = manager.list_servers()
    assert server_name not in servers
    logger.info("Verified: Server removed successfully.")
    
    # Cleanup
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)
        
    logger.success("Verification Passed: MCP Manager flow.")

    logger.success("Verification Passed: MCP Manager flow.")

