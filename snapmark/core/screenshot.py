import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import mss
from PIL import Image


class ScreenshotCapture:
    def __init__(self, output_dir: str = "SnapMarkData"):
        self.output_dir = Path(output_dir)
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        now = datetime.now()
        date_path = self.output_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = f"screen_{timestamp}.png"
        
        date_path = self._ensure_output_dir()
        filepath = date_path / filename
        
        with mss.mss() as sct:
            if region:
                monitor = {"top": region[1], "left": region[0], 
                          "width": region[2] - region[0], "height": region[3] - region[1]}
            else:
                monitor = sct.monitors[1]
            
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(str(filepath))
        
        return str(filepath)
    
    def capture_window(self) -> str:
        return self.capture_screen()
    
    def get_latest_screenshot_dir(self) -> Path:
        now = datetime.now()
        return self.output_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"