import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QListWidget, QSplitter,
    QSystemTrayIcon, QMenu, QAction, QMessageBox, QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QFont

# macOS compatibility
if sys.platform == 'darwin':
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

from ..core.screenshot import ScreenshotCapture
from ..core.ocr import OCRProcessor
from ..core.markdown_generator import MarkdownGenerator
from ..core.hotkey import HotkeyManager


class ScreenshotWorker(QThread):
    screenshot_taken = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, capture, ocr, md_gen):
        super().__init__()
        self.capture = capture
        self.ocr = ocr
        self.md_gen = md_gen
        
    def run(self):
        try:
            image_path = self.capture.capture_screen()
            ocr_text = self.ocr.extract_text(image_path)
            md_path = self.md_gen.create_markdown_note(image_path, ocr_text)
            self.screenshot_taken.emit(md_path)
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.capture = ScreenshotCapture()
        self.ocr = OCRProcessor()
        self.md_gen = MarkdownGenerator()
        self.hotkey_manager = HotkeyManager()
        
        self.init_ui()
        self.setup_system_tray()
        self.setup_hotkeys()
        
    def init_ui(self):
        self.setWindowTitle("SnapMark - Screenshot & OCR Tool")
        self.setGeometry(100, 100, 1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Control panel
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout(control_group)
        
        self.screenshot_btn = QPushButton("Take Screenshot (Cmd+Shift+3)")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        control_layout.addWidget(self.screenshot_btn)
        
        self.hotkey_enabled = QCheckBox("Enable Hotkeys")
        self.hotkey_enabled.setChecked(True)
        self.hotkey_enabled.toggled.connect(self.toggle_hotkeys)
        control_layout.addWidget(self.hotkey_enabled)
        
        layout.addWidget(control_group)
        
        # Main content area
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - File list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Recent Screenshots"))
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.load_note)
        left_layout.addWidget(self.file_list)
        
        # Right panel - Content viewer
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        right_layout.addWidget(self.image_label)
        
        right_layout.addWidget(QLabel("Markdown Content:"))
        self.content_text = QTextEdit()
        self.content_text.setFont(QFont("Monaco", 12))
        right_layout.addWidget(self.content_text)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        self.refresh_file_list()
        
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple default icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.blue)
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        
        tray_menu = QMenu()
        
        screenshot_action = QAction("Take Screenshot", self)
        screenshot_action.triggered.connect(self.take_screenshot)
        tray_menu.addAction(screenshot_action)
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def setup_hotkeys(self):
        try:
            self.hotkey_manager.register_hotkey("cmd+shift+3", self.take_screenshot)
            self.hotkey_manager.start_listening()  # Start listening immediately
            self.statusBar().showMessage("Global hotkeys enabled (Cmd+Shift+3)")
        except Exception as e:
            self.statusBar().showMessage(f"Hotkey setup failed: {e}")
    
    def toggle_hotkeys(self, enabled):
        if enabled:
            if not self.hotkey_manager.is_active():
                self.setup_hotkeys()
        else:
            self.hotkey_manager.stop_listening()
            self.statusBar().showMessage("Hotkeys disabled")
    
    def take_screenshot(self):
        self.statusBar().showMessage("Taking screenshot...")
        
        self.worker = ScreenshotWorker(self.capture, self.ocr, self.md_gen)
        self.worker.screenshot_taken.connect(self.on_screenshot_taken)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_screenshot_taken(self, md_path):
        self.statusBar().showMessage(f"Screenshot saved: {Path(md_path).name}")
        self.refresh_file_list()
        
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "SnapMark",
                "Screenshot captured and processed!",
                QSystemTrayIcon.Information,
                2000
            )
    
    def on_error(self, error_msg):
        self.statusBar().showMessage(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
    
    def refresh_file_list(self):
        self.file_list.clear()
        
        notes = self.md_gen.get_daily_notes()
        for note_path in sorted(notes, key=lambda x: x.stat().st_mtime, reverse=True):
            self.file_list.addItem(note_path.stem)
    
    def load_note(self, item):
        note_name = item.text()
        date_path = self.capture.get_latest_screenshot_dir()
        md_path = date_path / f"{note_name}.md"
        
        if md_path.exists():
            # Load markdown content
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.content_text.setPlainText(content)
            
            # Load image
            img_path = date_path / f"{note_name}.png"
            if img_path.exists():
                pixmap = QPixmap(str(img_path))
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        self.image_label.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                else:
                    self.image_label.setText("Failed to load image")
            else:
                self.image_label.setText("Image not found")
    
    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            # Show tray message when minimizing
            self.tray_icon.showMessage(
                "SnapMark",
                "Application minimized to tray. Global hotkeys remain active.",
                QSystemTrayIcon.Information,
                3000
            )
        else:
            self.hotkey_manager.stop_listening()
            event.accept()