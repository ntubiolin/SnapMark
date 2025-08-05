import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QListWidget, QSplitter,
    QSystemTrayIcon, QMenu, QGroupBox, QCheckBox, QComboBox,
    QScrollArea, QListWidgetItem, QFileDialog, QMessageBox,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QRubberBand, QDialog, QDialogButtonBox, QTextBrowser
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect, QPoint, QRectF, QSize
from PyQt6.QtGui import (
    QIcon, QPixmap, QFont, QAction, QPainter, QPen, QColor,
    QImage, QKeySequence, QShortcut, QClipboard
)

# macOS compatibility
if sys.platform == 'darwin':
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

from ..core.screenshot import ScreenshotCapture
from ..core.ocr import OCRProcessor
from ..core.vlm import VLMProcessor
from ..core.markdown_generator import MarkdownGenerator
from ..core.hotkey import HotkeyManager
from ..core.ai_summary import AISummaryGenerator
from ..core.ai_chat import AIChat
from ..config import Config


class AnnotationGraphicsView(QGraphicsView):
    """Custom QGraphicsView for image display with annotation support"""
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.pixmap_item = None
        self.annotations = []
        self.current_rect = None
        self.start_point = None
        self.drawing = False
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
    def load_image(self, image_path: str):
        """Load an image into the view"""
        pixmap = QPixmap(image_path)
        if self.pixmap_item:
            self.scene.removeItem(self.pixmap_item)
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(pixmap.rect())
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def enable_annotation_mode(self):
        """Enable red box annotation mode"""
        self.drawing = True
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def disable_annotation_mode(self):
        """Disable annotation mode"""
        self.drawing = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
    def mousePressEvent(self, event):
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            self.start_point = self.mapToScene(event.pos())
            self.current_rect = self.scene.addRect(
                QRectF(self.start_point, self.start_point),
                QPen(QColor(255, 0, 0), 3)
            )
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.drawing and self.current_rect and self.start_point:
            end_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, end_point).normalized()
            self.current_rect.setRect(rect)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            if self.current_rect:
                self.annotations.append(self.current_rect)
                self.current_rect = None
                self.start_point = None
        super().mouseReleaseEvent(event)
        
    def clear_annotations(self):
        """Clear all annotations"""
        for rect in self.annotations:
            self.scene.removeItem(rect)
        self.annotations.clear()
        
    def get_annotated_image(self) -> Optional[QPixmap]:
        """Get the current view with annotations as a QPixmap"""
        if not self.pixmap_item:
            return None
            
        # Create a pixmap of the scene
        pixmap = QPixmap(self.scene.sceneRect().size().toSize())
        pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(pixmap)
        self.scene.render(painter)
        painter.end()
        
        return pixmap


class ChatMessage(QWidget):
    """Widget for displaying a single chat message"""
    
    def __init__(self, message: str, is_user: bool = True):
        super().__init__()
        layout = QHBoxLayout(self)
        
        # Message bubble
        self.message_label = QTextBrowser()
        self.message_label.setMarkdown(message)
        self.message_label.setReadOnly(True)
        self.message_label.setOpenExternalLinks(True)
        
        # Style based on sender
        if is_user:
            self.message_label.setStyleSheet("""
                QTextBrowser {
                    background-color: #007AFF;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                }
            """)
            layout.addStretch()
            layout.addWidget(self.message_label, 7)
        else:
            self.message_label.setStyleSheet("""
                QTextBrowser {
                    background-color: #E5E5EA;
                    color: black;
                    border-radius: 10px;
                    padding: 10px;
                }
            """)
            layout.addWidget(self.message_label, 7)
            layout.addStretch()
            
        # Adjust height based on content
        self.message_label.document().contentsChanged.connect(self.adjust_height)
        self.adjust_height()
        
    def adjust_height(self):
        """Adjust widget height based on content"""
        doc_height = self.message_label.document().size().height()
        self.message_label.setFixedHeight(int(doc_height) + 20)


class AIConversationWidget(QWidget):
    """Widget for AI conversation interface"""
    
    send_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Chat history
        self.chat_scroll = QScrollArea()
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_widget)
        self.chat_scroll.setWidgetResizable(True)
        layout.addWidget(self.chat_scroll)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_field.setPlaceholderText("輸入訊息或指令...")
        
        self.send_button = QPushButton("發送")
        self.send_button.clicked.connect(self.send_current_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)
        
        # Keyboard shortcut for sending
        self.send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.send_shortcut.activated.connect(self.send_current_message)
        
    def send_current_message(self):
        """Send the current message"""
        message = self.input_field.toPlainText().strip()
        if message:
            self.add_message(message, is_user=True)
            self.send_message.emit(message)
            self.input_field.clear()
            
    def add_message(self, message: str, is_user: bool = True):
        """Add a message to the chat history"""
        # Remove the stretch
        count = self.chat_layout.count()
        if count > 0:
            item = self.chat_layout.itemAt(count - 1)
            if item and item.spacerItem():
                self.chat_layout.removeItem(item)
                
        # Add message
        msg_widget = ChatMessage(message, is_user)
        self.chat_layout.addWidget(msg_widget)
        
        # Add stretch back
        self.chat_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))


class SummaryDialog(QDialog):
    """Dialog for summary generation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生成整合報告")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Prompt input
        layout.addWidget(QLabel("輸入整合報告的提示詞："))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "例如：請總結今天的所有技術筆記，重點關注 API 設計和性能優化的部分..."
        )
        self.prompt_input.setMaximumHeight(150)
        layout.addWidget(self.prompt_input)
        
        # Options
        options_layout = QHBoxLayout()
        
        # Date range
        options_layout.addWidget(QLabel("天數範圍："))
        self.days_input = QComboBox()
        self.days_input.addItems(["1", "3", "7", "14", "30"])
        options_layout.addWidget(self.days_input)
        
        # Output format
        options_layout.addWidget(QLabel("輸出格式："))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "PDF"])
        options_layout.addWidget(self.format_combo)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_settings(self) -> Dict[str, Any]:
        """Get the summary settings"""
        return {
            "prompt": self.prompt_input.toPlainText(),
            "days": int(self.days_input.currentText()),
            "format": self.format_combo.currentText()
        }


class EnhancedMainWindow(QMainWindow):
    """Enhanced main window with all features from 01_UI.md"""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.capture = ScreenshotCapture()
        self.ocr = OCRProcessor()
        self.vlm = VLMProcessor()
        self.md_gen = MarkdownGenerator()
        self.hotkey_manager = HotkeyManager()
        self.ai_summary = AISummaryGenerator()
        self.ai_chat = None  # Will be initialized when model is selected
        
        self.current_screenshot_path = None
        self.current_markdown_path = None
        
        self.init_ui()
        # Temporarily disable system tray to avoid threading issues on macOS
        # self.setup_system_tray()
        self.setup_hotkeys()
        self.load_config()
        
    def init_ui(self):
        self.setWindowTitle("SnapMark - AI 輔助截圖筆記工具")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left side - Chat interface
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("AI 對話"))
        self.chat_widget = AIConversationWidget()
        self.chat_widget.send_message.connect(self.process_ai_message)
        left_layout.addWidget(self.chat_widget)
        
        # Right side - Screenshot and controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Screenshot display
        self.image_view = AnnotationGraphicsView()
        right_layout.addWidget(self.image_view)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.copy_button = QPushButton("📋 複製圖片")
        self.copy_button.clicked.connect(self.copy_screenshot)
        self.copy_button.setEnabled(False)
        controls_layout.addWidget(self.copy_button)
        
        self.annotate_button = QPushButton("🔴 紅框標記")
        self.annotate_button.setCheckable(True)
        self.annotate_button.toggled.connect(self.toggle_annotation_mode)
        self.annotate_button.setEnabled(False)
        controls_layout.addWidget(self.annotate_button)
        
        self.clear_annotations_button = QPushButton("清除標記")
        self.clear_annotations_button.clicked.connect(self.image_view.clear_annotations)
        self.clear_annotations_button.setEnabled(False)
        controls_layout.addWidget(self.clear_annotations_button)
        
        controls_layout.addStretch()
        right_layout.addLayout(controls_layout)
        
        # Settings panel
        settings_group = QGroupBox("設定")
        settings_layout = QVBoxLayout(settings_group)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI 模型："))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "o1-preview",
            "o1-mini"
        ])
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        settings_layout.addLayout(model_layout)
        
        # Path settings
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("儲存路徑："))
        self.path_input = QLineEdit()
        self.path_input.setText(self.config.get_output_dir())
        self.browse_button = QPushButton("瀏覽")
        self.browse_button.clicked.connect(self.browse_output_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        settings_layout.addLayout(path_layout)
        
        # Summary button
        self.summary_button = QPushButton("📄 生成整合報告")
        self.summary_button.clicked.connect(self.show_summary_dialog)
        settings_layout.addWidget(self.summary_button)
        
        right_layout.addWidget(settings_group)
        
        # Add panels to splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("就緒")
        
    def setup_system_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 122, 255))
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        
        # Tray menu
        tray_menu = QMenu()
        
        screenshot_action = QAction("截圖", self)
        screenshot_action.triggered.connect(self.take_screenshot)
        tray_menu.addAction(screenshot_action)
        
        show_action = QAction("顯示視窗", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("結束", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def setup_hotkeys(self):
        """Setup global hotkeys"""
        try:
            hotkey = self.config.get("hotkey", "cmd+shift+3")
            self.hotkey_manager.register_hotkey(hotkey, self.take_screenshot_and_show)
            self.hotkey_manager.start_listening()
            self.statusBar().showMessage(f"快捷鍵已啟用: {hotkey}")
        except Exception as e:
            self.statusBar().showMessage(f"快捷鍵設定失敗: {e}")
            
    def load_config(self):
        """Load configuration"""
        # Load model preference
        preferred_model = self.config.get("ai_model", "gpt-4o-mini")
        index = self.model_combo.findText(preferred_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
            
    def take_screenshot(self):
        """Take a screenshot"""
        try:
            # Hide window during screenshot
            was_visible = self.isVisible()
            if was_visible:
                self.hide()
                QApplication.processEvents()
            
            # Small delay to ensure window is hidden
            QTimer.singleShot(100, lambda: self._capture_screenshot(was_visible))
            
        except Exception as e:
            self.show()
            QMessageBox.critical(self, "錯誤", f"截圖失敗: {e}")
            
    def _capture_screenshot(self, was_visible=True):
        """Actual screenshot capture"""
        try:
            image_path = self.capture.capture_screen()
            self.current_screenshot_path = image_path
            
            # Process with OCR
            ocr_text = self.ocr.extract_text(image_path)
            
            # Process with VLM if available
            vlm_description = None
            if self.vlm.is_available():
                vlm_description = self.vlm.describe_image(image_path)
                
            # Create markdown note
            md_path = self.md_gen.create_markdown_note(image_path, ocr_text, vlm_description)
            self.current_markdown_path = md_path
            
            # Show window and display screenshot if it was visible before
            if was_visible:
                self.show()
                self.activateWindow()
                self.raise_()
            self.display_screenshot(image_path)
            
            # Add initial AI message
            self.chat_widget.add_message(
                f"截圖已完成！我可以幫您分析這張圖片或回答相關問題。\n\n"
                f"圖片路徑: {image_path}\n"
                f"Markdown 筆記: {md_path}",
                is_user=False
            )
            
            self.statusBar().showMessage(f"截圖已儲存: {Path(image_path).name}")
            
        except Exception as e:
            if was_visible:
                self.show()
            QMessageBox.critical(self, "錯誤", f"處理截圖時發生錯誤: {e}")
            
    def take_screenshot_and_show(self):
        """Take screenshot and show window (for hotkey)"""
        # Use QTimer to ensure we're on the main thread
        QTimer.singleShot(0, self.take_screenshot)
        
    def display_screenshot(self, image_path: str):
        """Display screenshot in the image view"""
        self.image_view.load_image(image_path)
        self.copy_button.setEnabled(True)
        self.annotate_button.setEnabled(True)
        self.clear_annotations_button.setEnabled(True)
        
    def copy_screenshot(self):
        """Copy screenshot to clipboard"""
        if self.current_screenshot_path and Path(self.current_screenshot_path).exists():
            pixmap = self.image_view.get_annotated_image()
            if pixmap:
                QApplication.clipboard().setPixmap(pixmap)
                self.statusBar().showMessage("圖片已複製到剪貼簿")
                
    def toggle_annotation_mode(self, checked: bool):
        """Toggle annotation mode"""
        if checked:
            self.image_view.enable_annotation_mode()
            self.annotate_button.setText("🔴 停止標記")
        else:
            self.image_view.disable_annotation_mode()
            self.annotate_button.setText("🔴 紅框標記")
            
    def process_ai_message(self, message: str):
        """Process user message with AI"""
        try:
            # Initialize AI chat if needed
            if not self.ai_chat:
                self.initialize_ai_chat()
                
            # Send message with current screenshot if available
            if self.current_screenshot_path and Path(self.current_screenshot_path).exists():
                response = self.ai_chat.send_message(message, self.current_screenshot_path)
            else:
                response = self.ai_chat.send_message(message)
                
            self.chat_widget.add_message(response, is_user=False)
            
        except Exception as e:
            error_msg = f"AI 處理錯誤: {str(e)}"
            self.chat_widget.add_message(error_msg, is_user=False)
            self.statusBar().showMessage(error_msg)
        
    def initialize_ai_chat(self):
        """Initialize AI chat with selected model"""
        model = self.model_combo.currentText()
        
        try:
            # Determine provider from model name
            provider = None
            if model.startswith(("gpt", "o1")):
                provider = "openai"
            elif model.startswith("claude"):
                provider = "claude"
            elif model.startswith("gemini"):
                provider = "gemini"
            else:
                # Assume ollama for other models
                provider = "ollama"
                
            self.ai_chat = AIChat(provider=provider, model=model)
            
        except Exception as e:
            raise Exception(f"無法初始化 AI 聊天: {str(e)}")
            
    def on_model_changed(self, model: str):
        """Handle model selection change"""
        self.config.set("ai_model", model)
        self.statusBar().showMessage(f"已切換到模型: {model}")
        
        # Reinitialize AI chat with new model
        self.ai_chat = None
        
    def browse_output_path(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "選擇儲存目錄", 
            self.path_input.text()
        )
        if directory:
            self.path_input.setText(directory)
            self.config.set("output_directory", directory)
            
    def show_summary_dialog(self):
        """Show summary generation dialog"""
        dialog = SummaryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            self.generate_summary(settings)
            
    def generate_summary(self, settings: Dict[str, Any]):
        """Generate summary report"""
        try:
            self.statusBar().showMessage("正在生成整合報告...")
            
            # 1. Collect markdown files from specified date range
            notes = self.collect_notes_from_date_range(settings["days"])
            
            if not notes:
                QMessageBox.warning(self, "警告", f"在過去 {settings['days']} 天內未找到任何筆記。")
                return
                
            # 2. Generate summary using AI
            current_model = self.model_combo.currentText()
            summary = self.ai_summary.generate_custom_summary(
                notes, settings["prompt"], current_model, settings["days"]
            )
            
            # 3. Save as requested format
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.path_input.text())
            
            if settings["format"] == "Markdown":
                output_file = output_dir / f"summary_{timestamp}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 整合報告 - {datetime.now().strftime('%Y年%m月%d日')}\n\n")
                    f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**資料範圍**: 過去 {settings['days']} 天\n")
                    f.write(f"**AI 模型**: {current_model}\n\n")
                    f.write("## 用戶提示\n\n")
                    f.write(f"{settings['prompt']}\n\n")
                    f.write("## AI 摘要\n\n")
                    f.write(summary)
            else:  # PDF
                # For PDF generation, we'd need to install reportlab or similar
                # For now, just save as markdown and inform user
                output_file = output_dir / f"summary_{timestamp}.md" 
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 整合報告 - {datetime.now().strftime('%Y年%m月%d日')}\n\n")
                    f.write(summary)
                    
                QMessageBox.information(
                    self, "提醒", 
                    "PDF 功能尚未實現，已儲存為 Markdown 格式。\n"
                    "您可以使用工具將 Markdown 轉換為 PDF。"
                )
            
            self.statusBar().showMessage(f"整合報告已儲存: {output_file.name}")
            QMessageBox.information(self, "完成", f"整合報告已生成並儲存至:\n{output_file}")
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"生成報告時發生錯誤: {e}")
            
    def collect_notes_from_date_range(self, days: int) -> List[str]:
        """Collect markdown notes from the specified date range"""
        notes = []
        output_dir = Path(self.path_input.text())
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Search for markdown files in the SnapMarkData structure
        for md_file in output_dir.rglob("*.md"):
            try:
                # Check file modification time
                if datetime.fromtimestamp(md_file.stat().st_mtime) >= cutoff_date:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        notes.append(f"**檔案**: {md_file.name}\n**路徑**: {md_file}\n\n{content}")
            except Exception as e:
                continue  # Skip files that can't be read
                
        return notes
            
    def closeEvent(self, event):
        """Handle window close event"""
        # For now, just close the application
        self.hotkey_manager.stop_listening()
        event.accept()