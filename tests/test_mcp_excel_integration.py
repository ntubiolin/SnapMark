#!/usr/bin/env python3
"""
Test function for MCPClient.process_screenshot_data() with real Excel MCP server.
This test demonstrates proper MCP stdio protocol communication and Excel file creation.
"""

import asyncio
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import tempfile
import subprocess
from snapmark.core.mcp_client import MCPClient, MCPServerConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_process_screenshot_data_with_real_mcp_protocol():
    """Test process_screenshot_data with the real Excel MCP server."""
    
    # Test data paths
    test_dir = Path(__file__).parent / "test_data"
    image_path = str(test_dir / "screen_13-32-20.png")
    md_path = str(test_dir / "screen_13-32-20.md")
    
    # Extract test data
    ocr_text = """@ Chrome File Edit View History Bookmarks Profiles Tab Window Help xX © ®W (A) @ © Q Sf Tuedugsd 1:32PM
CoWoS-S: Mainstream intermediary board
CoWoS-R: Fewer layers, reduced cost
CoWoS-L: Internal interconnection with many HBM"""
    
    vlm_description = "Screenshot showing TSMC CoWoS technology types with diagrams"
    
    print("=== Test: Real Excel MCP Server ===")
    print(f"Image: {Path(image_path).name}")
    print(f"Markdown: {Path(md_path).name}")
    
    # Configure the real Excel MCP server
    excel_server_config = MCPServerConfig(
        name="excel",
        command="/Users/linyusheng/.local/bin/excel-mcp-server",
        args=["stdio"],
        enabled=True
    )
    
    # Use async context manager for proper cleanup
    async with MCPClient() as mcp_client:
        # Add server to client
        mcp_client.add_server(excel_server_config)
        
        try:
            # Test the process_screenshot_data method with custom prompt
            custom_prompt = "Create a comprehensive analysis focusing on TSMC semiconductor technology, specifically CoWoS packaging types, their costs, and technical advantages. Then summarize the key comparisons into excel."
            results = await mcp_client.process_screenshot_data(
                image_path=image_path,
                markdown_path=md_path,
                ocr_text=ocr_text,
                vlm_description=vlm_description,
                custom_prompt=custom_prompt
            )
            
            print("\n=== MCP Processing Results ===")
            print(json.dumps(results, indent=2))
            
            # Verify results
            assert "mcp_use_agent" in results, "MCP agent results not found"
            assert results["mcp_use_agent"]["success"], "MCP agent processing failed"
            
            # Check if any Excel files were created
            excel_files = list(Path("SnapMarkData/excel_exports").glob("*.xlsx"))
            print(f"\n✅ Found {len(excel_files)} Excel files created")
            for excel_file in excel_files:
                print(f"   - {excel_file.name}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False




def main():
    """Run all MCP integration tests."""
    print("=== Testing MCP Excel Integration ===\n")
    
    async def run_tests():
        # Test: Real MCP protocol communication with actual screenshot data
        success = await test_process_screenshot_data_with_real_mcp_protocol()
        
        if success:
            print("\n✅ All MCP integration tests passed!")
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
    
    # Use asyncio.run for proper event loop management and cleanup
    try:
        success = asyncio.run(run_tests())
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()