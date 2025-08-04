#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path

# macOS compatibility - must be set before importing PyQt5
if sys.platform == 'darwin':
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

from PyQt5.QtWidgets import QApplication

from .gui.main_window import MainWindow
from .background import BackgroundService
from .core.screenshot import ScreenshotCapture
from .core.ocr import OCRProcessor
from .core.markdown_generator import MarkdownGenerator
from .core.ai_summary import AISummaryGenerator
from .utils.search import SearchEngine, FileManager
from .utils.scheduler import TaskScheduler


def create_cli_parser():
    parser = argparse.ArgumentParser(description="SnapMark2 - Screenshot & OCR Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch GUI application')
    
    # Background service command
    bg_parser = subparsers.add_parser('background', help='Run background service with global hotkeys only')
    bg_parser.add_argument('--output', type=str, help='Output directory')
    
    # Screenshot command
    screenshot_parser = subparsers.add_parser('screenshot', help='Take screenshot')
    screenshot_parser.add_argument('--region', type=str, help='Screenshot region as x,y,w,h')
    screenshot_parser.add_argument('--output', type=str, help='Output directory')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search notes')
    search_parser.add_argument('query', type=str, help='Search query')
    search_parser.add_argument('--tags', type=str, nargs='+', help='Filter by tags')
    search_parser.add_argument('--limit', type=int, default=10, help='Limit results')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Generate summary')
    summary_parser.add_argument('--days', type=int, default=1, help='Days to summarize')
    summary_parser.add_argument('--output', type=str, help='Output file')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Rebuild search index')
    
    return parser


def cmd_screenshot(args):
    capture = ScreenshotCapture(args.output or "SnapMarkData")
    ocr = OCRProcessor()
    md_gen = MarkdownGenerator(args.output or "SnapMarkData")
    
    region = None
    if args.region:
        try:
            x, y, w, h = map(int, args.region.split(','))
            region = (x, y, x + w, y + h)
        except ValueError:
            print("Invalid region format. Use: x,y,w,h")
            return
    
    try:
        image_path = capture.capture_screen(region)
        print(f"Screenshot saved: {image_path}")
        
        ocr_text = ocr.extract_text(image_path)
        md_path = md_gen.create_markdown_note(image_path, ocr_text)
        print(f"Markdown note created: {md_path}")
        
        # Index the new note
        search_engine = SearchEngine(args.output or "SnapMarkData")
        search_engine.index_note(md_path)
        
    except Exception as e:
        print(f"Error: {e}")


def cmd_search(args):
    search_engine = SearchEngine()
    results = search_engine.search(args.query, tags=args.tags, limit=args.limit)
    
    if not results:
        print("No results found.")
        return
    
    print(f"Found {len(results)} results:")
    print("-" * 50)
    
    for result in results:
        print(f"Title: {result['title']}")
        print(f"File: {result['filename']}")
        print(f"Created: {result['created_date']}")
        if result['tags']:
            print(f"Tags: {result['tags']}")
        print(f"Path: {result['filepath']}")
        print("-" * 50)


def cmd_summary(args):
    try:
        ai_gen = AISummaryGenerator()
        md_gen = MarkdownGenerator()
        file_manager = FileManager()
        
        recent_files = file_manager.get_recent_files(args.days)
        
        if not recent_files:
            print(f"No notes found in the last {args.days} days.")
            return
        
        note_contents = []
        for file_path in recent_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            note_contents.append(content)
        
        summary = ai_gen.generate_daily_summary(note_contents)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"Summary saved to: {args.output}")
        else:
            print("Summary:")
            print("=" * 50)
            print(summary)
        
    except Exception as e:
        print(f"Error generating summary: {e}")


def cmd_index(args):
    search_engine = SearchEngine()
    print("Rebuilding search index...")
    search_engine.rebuild_index()
    print("Search index rebuilt successfully.")


def main():
    parser = create_cli_parser()
    
    if len(sys.argv) == 1:
        # No arguments provided, launch GUI
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    
    args = parser.parse_args()
    
    if args.command == 'gui' or args.command is None:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    
    elif args.command == 'background':
        service = BackgroundService()
        if args.output:
            # Set custom output directory if provided
            service.capture = ScreenshotCapture(args.output)
            service.md_gen = MarkdownGenerator(args.output)
            service.search_engine = SearchEngine(args.output)
        sys.exit(0 if service.start() else 1)
    
    elif args.command == 'screenshot':
        cmd_screenshot(args)
    
    elif args.command == 'search':
        cmd_search(args)
    
    elif args.command == 'summary':
        cmd_summary(args)
    
    elif args.command == 'index':
        cmd_index(args)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()