#!/usr/bin/env python3
"""Background service for SnapMark with global hotkeys only."""

import sys
import signal
import time
from pathlib import Path

from .core.screenshot import ScreenshotCapture
from .core.ocr import OCRProcessor
from .core.vlm import VLMProcessor
from .core.markdown_generator import MarkdownGenerator
from .core.hotkey import HotkeyManager
from .core.mcp_client import MCPClient
from .utils.search import SearchEngine
from .config import ConfigManager


class BackgroundService:
    def __init__(self):
        self.config = ConfigManager()
        self.capture = ScreenshotCapture()
        self.ocr = OCRProcessor()
        self.vlm = VLMProcessor()
        self.md_gen = MarkdownGenerator()
        self.hotkey_manager = HotkeyManager()
        self.search_engine = SearchEngine()
        self.mcp_client = MCPClient()
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
    
    def setup_hotkeys(self):
        """Setup global hotkeys for background operation."""
        try:
            self.hotkey_manager.register_hotkey("cmd+shift+3", self.take_screenshot)
            self.hotkey_manager.register_hotkey("cmd+shift+4", self.take_region_screenshot)
            print("✅ Global hotkeys registered:")
            print("   Cmd+Shift+3: Full screen screenshot")
            print("   Cmd+Shift+4: Region screenshot (not implemented yet)")
            return True
        except Exception as e:
            print(f"❌ Failed to setup hotkeys: {e}")
            return False
    
    def take_screenshot(self):
        """Take a screenshot and process it."""
        try:
            print("📸 Taking screenshot...")
            
            # Capture screenshot
            image_path = self.capture.capture_screen()
            print(f"   Screenshot saved: {Path(image_path).name}")
            
            # Process with OCR
            ocr_text = self.ocr.extract_text(image_path)
            print(f"   OCR processed: {len(ocr_text)} characters extracted")
            
            # Process with VLM if enabled and available
            vlm_description = None
            config = self.config.config
            if config.get('vlm', {}).get('enabled', False):
                if self.vlm.is_available():
                    print("   Generating VLM description...")
                    vlm_description = self.vlm.describe_image(image_path)
                    print(f"   VLM description generated: {len(vlm_description)} characters")
                else:
                    print("   VLM enabled but service not available")
            
            # Generate Markdown
            md_path = self.md_gen.create_markdown_note(image_path, ocr_text, vlm_description)
            print(f"   Markdown created: {Path(md_path).name}")
            
            # Index for search
            self.search_engine.index_note(md_path)
            print("   Note indexed for search")
            
            # Process with MCP servers if enabled
            if self.mcp_client.is_enabled():
                print("   Processing with MCP servers...")
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Get custom prompt from config to trigger mcp-use agent processing
                    custom_prompt = self.config.get('mcp.default_prompt')
                    
                    mcp_results = loop.run_until_complete(
                        self.mcp_client.process_screenshot_data(
                            image_path, md_path, ocr_text, vlm_description, custom_prompt
                        )
                    )
                    loop.close()
                    
                    for server_name, result in mcp_results.items():
                        if "error" in result:
                            print(f"   MCP {server_name}: Error - {result['error']}")
                        else:
                            print(f"   MCP {server_name}: Success")
                            
                except Exception as e:
                    print(f"   MCP processing failed: {e}")
            
            # Show notification-style message
            print(f"✅ Screenshot processed successfully!")
            
        except Exception as e:
            print(f"❌ Error taking screenshot: {e}")
    
    def take_region_screenshot(self):
        """Placeholder for region screenshot."""
        print("📍 Region screenshot not yet implemented")
    
    def start(self):
        """Start the background service."""
        print("🚀 Starting SnapMark Background Service")
        print("=" * 50)
        
        if not self.setup_hotkeys():
            return False
        
        self.running = True
        self.hotkey_manager.start_listening()
        
        print("📱 Service running in background...")
        print("   Press Ctrl+C to stop")
        print("   Use global hotkeys to take screenshots")
        
        try:
            # Keep the service running
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the background service."""
        print("\n🛑 Stopping background service...")
        self.running = False
        self.hotkey_manager.stop_listening()
        print("✅ Service stopped")


def run_background_service():
    """Run the background service."""
    service = BackgroundService()
    return service.start()


if __name__ == "__main__":
    run_background_service()