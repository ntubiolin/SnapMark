#!/usr/bin/env python3
"""Background service for SnapMark2 with global hotkeys only."""

import sys
import signal
import time
from pathlib import Path

from .core.screenshot import ScreenshotCapture
from .core.ocr import OCRProcessor
from .core.markdown_generator import MarkdownGenerator
from .core.hotkey import HotkeyManager
from .utils.search import SearchEngine


class BackgroundService:
    def __init__(self):
        self.capture = ScreenshotCapture()
        self.ocr = OCRProcessor()
        self.md_gen = MarkdownGenerator()
        self.hotkey_manager = HotkeyManager()
        self.search_engine = SearchEngine()
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
            
            # Generate Markdown
            md_path = self.md_gen.create_markdown_note(image_path, ocr_text)
            print(f"   Markdown created: {Path(md_path).name}")
            
            # Index for search
            self.search_engine.index_note(md_path)
            print("   Note indexed for search")
            
            # Show notification-style message
            print(f"✅ Screenshot processed successfully!")
            
        except Exception as e:
            print(f"❌ Error taking screenshot: {e}")
    
    def take_region_screenshot(self):
        """Placeholder for region screenshot."""
        print("📍 Region screenshot not yet implemented")
    
    def start(self):
        """Start the background service."""
        print("🚀 Starting SnapMark2 Background Service")
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