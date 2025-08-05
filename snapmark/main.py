#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path

# macOS compatibility - must be set before importing PyQt
if sys.platform == 'darwin':
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

try:
    from PyQt6.QtWidgets import QApplication
    from .gui.enhanced_window import EnhancedMainWindow as MainWindow
    PYQT_VERSION = 6
except ImportError:
    from PyQt5.QtWidgets import QApplication
    from .gui.main_window import MainWindow
    PYQT_VERSION = 5
from .background import BackgroundService
from .core.screenshot import ScreenshotCapture
from .core.ocr import OCRProcessor
from .core.vlm import VLMProcessor
from .core.markdown_generator import MarkdownGenerator
from .core.ai_summary import AISummaryGenerator
from .core.mcp_client import MCPClient
from .utils.search import SearchEngine, FileManager
from .utils.scheduler import TaskScheduler


def create_cli_parser():
    parser = argparse.ArgumentParser(description="SnapMark - Screenshot & OCR Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch GUI application')
    gui_parser.add_argument('--streamlit', action='store_true', help='Use Streamlit interface instead of PyQt')
    
    # Streamlit command
    streamlit_parser = subparsers.add_parser('streamlit', help='Launch Streamlit web interface')
    
    # Background service command
    bg_parser = subparsers.add_parser('background', help='Run background service with global hotkeys only')
    bg_parser.add_argument('--output', type=str, help='Output directory')
    
    # Screenshot command
    screenshot_parser = subparsers.add_parser('screenshot', help='Take screenshot')
    screenshot_parser.add_argument('--region', type=str, help='Screenshot region as x,y,w,h')
    screenshot_parser.add_argument('--output', type=str, help='Output directory')
    screenshot_parser.add_argument('--vlm', action='store_true', help='Use VLM for image description')
    screenshot_parser.add_argument('--mcp', action='store_true', help='Process with MCP servers')
    
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
    
    # VLM command
    vlm_parser = subparsers.add_parser('vlm', help='Generate VLM description for existing image')
    vlm_parser.add_argument('image_path', type=str, help='Path to image file')
    vlm_parser.add_argument('--prompt', type=str, help='Custom prompt for image description')
    vlm_parser.add_argument('--action-items', action='store_true', help='Extract action items from image')
    vlm_parser.add_argument('--key-info', action='store_true', help='Extract key information from image')
    
    # MCP command
    mcp_parser = subparsers.add_parser('mcp', help='MCP server management and testing')
    mcp_subparsers = mcp_parser.add_subparsers(dest='mcp_action', help='MCP actions')
    
    # MCP list servers
    mcp_list_parser = mcp_subparsers.add_parser('list', help='List configured MCP servers')
    
    # MCP test server
    mcp_test_parser = mcp_subparsers.add_parser('test', help='Test MCP server connection')
    mcp_test_parser.add_argument('server_name', type=str, help='Name of MCP server to test')
    
    # MCP process data
    mcp_process_parser = mcp_subparsers.add_parser('process', help='Process data with MCP servers')
    mcp_process_parser.add_argument('image_path', type=str, help='Path to image file')
    mcp_process_parser.add_argument('--markdown', type=str, help='Path to markdown file')
    
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
        
        vlm_description = None
        if args.vlm:
            vlm = VLMProcessor()
            if vlm.is_available():
                print("Generating image description with VLM...")
                vlm_description = vlm.describe_image(image_path)
                print("VLM description generated")
            else:
                print("Warning: VLM service not available. Make sure Ollama is running with gemma3n:e4b model.")
        
        md_path = md_gen.create_markdown_note(image_path, ocr_text, vlm_description)
        print(f"Markdown note created: {md_path}")
        
        # Index the new note
        search_engine = SearchEngine(args.output or "SnapMarkData")
        search_engine.index_note(md_path)
        
        # Process with MCP servers if requested
        if args.mcp:
            mcp_client = MCPClient()
            if mcp_client.is_enabled():
                print("Processing with MCP servers...")
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    mcp_results = loop.run_until_complete(
                        mcp_client.process_screenshot_data(
                            image_path, md_path, ocr_text, vlm_description
                        )
                    )
                    loop.close()
                    
                    for server_name, result in mcp_results.items():
                        if "error" in result:
                            print(f"MCP {server_name}: Error - {result['error']}")
                        else:
                            print(f"MCP {server_name}: Success")
                            
                except Exception as e:
                    print(f"MCP processing failed: {e}")
            else:
                print("Warning: MCP not enabled or no servers configured")
        
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


def cmd_vlm(args):
    vlm = VLMProcessor()
    
    if not vlm.is_available():
        print("Error: VLM service not available. Make sure Ollama is running with gemma3n:e4b model.")
        return
    
    image_path = args.image_path
    if not Path(image_path).exists():
        print(f"Error: Image file not found at {image_path}")
        return
    
    try:
        if args.action_items:
            print("Extracting action items from image...")
            result = vlm.extract_action_items_from_image(image_path)
        elif args.key_info:
            print("Extracting key information from image...")
            result = vlm.extract_key_information(image_path)
        elif args.prompt:
            print(f"Generating description with custom prompt...")
            result = vlm.describe_image(image_path, args.prompt)
        else:
            print("Generating image description...")
            result = vlm.describe_image(image_path)
        
        print("\nResult:")
        print("=" * 50)
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")


def cmd_mcp(args):
    mcp_client = MCPClient()
    
    if args.mcp_action == 'list':
        servers = mcp_client.list_servers()
        if not servers:
            print("No MCP servers configured")
            return
        
        print("Configured MCP servers:")
        for name in servers:
            server = mcp_client.servers[name]
            status = "enabled" if server.enabled else "disabled"
            print(f"  {name}: {server.command} {' '.join(server.args)} ({status})")
    
    elif args.mcp_action == 'test':
        server_name = args.server_name
        if server_name not in mcp_client.servers:
            print(f"Error: Server '{server_name}' not found")
            return
        
        server = mcp_client.servers[server_name]
        if not server.enabled:
            print(f"Error: Server '{server_name}' is disabled")
            return
        
        print(f"Testing MCP server: {server_name}")
        try:
            # Test with dummy data
            test_data = {
                "image_path": "/test/path.png",
                "markdown_path": "/test/path.md",
                "ocr_text": "Test OCR text",
                "vlm_description": "Test VLM description",
                "timestamp": 1234567890
            }
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                mcp_client._interact_with_server(server, test_data)
            )
            loop.close()
            
            print(f"Test successful: {result}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    elif args.mcp_action == 'process':
        image_path = args.image_path
        if not Path(image_path).exists():
            print(f"Error: Image file not found at {image_path}")
            return
        
        # Load OCR text and VLM description if available
        ocr = OCRProcessor()
        ocr_text = ocr.extract_text(image_path)
        
        markdown_path = args.markdown or None
        vlm_description = None
        
        print("Processing with MCP servers...")
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            mcp_results = loop.run_until_complete(
                mcp_client.process_screenshot_data(
                    image_path, markdown_path, ocr_text, vlm_description
                )
            )
            loop.close()
            
            print("\nMCP Processing Results:")
            print("=" * 50)
            for server_name, result in mcp_results.items():
                print(f"\n{server_name}:")
                if "error" in result:
                    print(f"  Error: {result['error']}")
                else:
                    print(f"  Success: {result}")
                    
        except Exception as e:
            print(f"MCP processing failed: {e}")


def cmd_streamlit(args):
    """Launch Streamlit web interface with background service"""
    import subprocess
    import sys
    import threading
    import time
    
    # Get the path to the streamlit app
    app_path = Path(__file__).parent / "gui" / "streamlit_app.py"
    
    def start_background_service():
        """Start the background service for global hotkeys"""
        try:
            time.sleep(2)  # Wait for Streamlit to start
            print("Starting background service for global hotkeys...")
            from .background import BackgroundService
            
            # Create background service in thread mode (no signal handlers)
            service = BackgroundService(thread_mode=True)
            service.start()
                
        except Exception as e:
            print(f"Background service error: {e}")
    
    try:
        # Set PYTHONPATH to include project root
        env = os.environ.copy()
        project_root = Path(__file__).parent.parent
        env['PYTHONPATH'] = str(project_root) + (os.pathsep + env.get('PYTHONPATH', ''))
        
        # Start background service in a separate thread
        bg_thread = threading.Thread(target=start_background_service, daemon=True)
        bg_thread.start()
        
        print("Starting Streamlit web interface...")
        print("Background service will handle global hotkeys (Cmd+Shift+3)")
        print("Streamlit will be available at: http://localhost:8501")
        
        # Launch streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(app_path),
            "--server.headless", "false",
            "--server.port", "8501"
        ], env=env)
    except KeyboardInterrupt:
        print("\nStreamlit app stopped.")
    except Exception as e:
        print(f"Error launching Streamlit app: {e}")


def main():
    parser = create_cli_parser()
    
    if len(sys.argv) == 1:
        # No arguments provided, launch GUI
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        window = MainWindow()
        window.show()
        
        if PYQT_VERSION == 6:
            sys.exit(app.exec())
        else:
            sys.exit(app.exec_())
    
    args = parser.parse_args()
    
    if args.command == 'gui' or args.command is None:
        if hasattr(args, 'streamlit') and args.streamlit:
            # Launch Streamlit interface
            cmd_streamlit(args)
        else:
            # Launch PyQt interface
            app = QApplication(sys.argv)
            app.setQuitOnLastWindowClosed(False)
            
            window = MainWindow()
            window.show()
            
            if PYQT_VERSION == 6:
                sys.exit(app.exec())
            else:
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
    
    elif args.command == 'vlm':
        cmd_vlm(args)
    
    elif args.command == 'mcp':
        cmd_mcp(args)
    
    elif args.command == 'streamlit':
        cmd_streamlit(args)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()