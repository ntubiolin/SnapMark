import streamlit as st
import io
import os
import sys
import asyncio
from pathlib import Path
from PIL import Image, ImageDraw
import base64
from datetime import datetime
import json

# Add parent directory to path for imports when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from snapmark.core.screenshot import ScreenshotCapture
    from snapmark.core.ocr import OCRProcessor
    from snapmark.core.vlm import VLMProcessor
    from snapmark.core.markdown_generator import MarkdownGenerator
    from snapmark.core.ai_summary import AISummaryGenerator
    from snapmark.core.ai_chat import AIChatProcessor
    from snapmark.core.mcp_client import MCPClient
    from snapmark.utils.search import SearchEngine, FileManager
    from snapmark.config import Config
except ImportError:
    # Fallback for relative imports
    from ..core.screenshot import ScreenshotCapture
    from ..core.ocr import OCRProcessor
    from ..core.vlm import VLMProcessor
    from ..core.markdown_generator import MarkdownGenerator
    from ..core.ai_summary import AISummaryGenerator
    from ..core.ai_chat import AIChatProcessor
    from ..core.mcp_client import MCPClient
    from ..utils.search import SearchEngine, FileManager
    from ..config import Config


def init_session_state():
    """Initialize session state variables"""
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'current_image' not in st.session_state:
        st.session_state.current_image = None
    if 'current_image_path' not in st.session_state:
        st.session_state.current_image_path = None
    if 'config' not in st.session_state:
        st.session_state.config = Config()
    if 'processors' not in st.session_state:
        st.session_state.processors = {
            'capture': ScreenshotCapture(),
            'ocr': OCRProcessor(),
            'vlm': VLMProcessor(),
            'md_gen': MarkdownGenerator(),
            'ai_summary': AISummaryGenerator(),
            'ai_chat': None,  # Initialize lazily when needed
            'mcp': MCPClient(),
            'search': SearchEngine(),
            'file_manager': FileManager()
        }
    if 'last_check_time' not in st.session_state:
        st.session_state.last_check_time = datetime.now()
    if 'auto_loaded_screenshot' not in st.session_state:
        st.session_state.auto_loaded_screenshot = None
    if 'background_service_start_time' not in st.session_state:
        st.session_state.background_service_start_time = datetime.now()
    if 'last_screenshot_count' not in st.session_state:
        st.session_state.last_screenshot_count = 0
    if 'last_summary' not in st.session_state:
        st.session_state.last_summary = None
    if 'last_summary_prompt' not in st.session_state:
        st.session_state.last_summary_prompt = None
    if 'last_summary_time' not in st.session_state:
        st.session_state.last_summary_time = None


def image_to_base64(image):
    """Convert PIL image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def copy_image_to_clipboard(image_path):
    """Copy image to clipboard (platform-specific)"""
    import platform
    import subprocess
    
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.run(["osascript", "-e", f'set the clipboard to (read file POSIX file "{image_path}" as «class PNGf»)'])
    elif system == "Windows":
        from PIL import Image
        import win32clipboard
        img = Image.open(image_path)
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
    elif system == "Linux":
        subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i", image_path])


def add_red_frame_annotation(image_path, x1, y1, x2, y2):
    """Add red frame annotation to image"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
    
    # Save annotated image
    annotated_path = image_path.replace(".png", "_annotated.png")
    img.save(annotated_path)
    return annotated_path


def get_ai_chat_processor(provider=None, model=None):
    """Get or initialize AI chat processor"""
    # Always reinitialize if provider/model changes
    if (st.session_state.processors['ai_chat'] is None or 
        (provider and model)):
        try:
            # Use config values if provider/model not specified
            if not provider:
                provider = st.session_state.config.get('ai_chat.default_provider', 'openai')
            if not model:
                model = st.session_state.config.get('ai_chat.default_model', 'gpt-4o-mini')
            
            st.session_state.processors['ai_chat'] = AIChatProcessor(provider, model)
        except Exception as e:
            st.error(f"Failed to initialize AI chat: {e}")
            return None
    
    return st.session_state.processors['ai_chat']


def get_background_service_status():
    """Get the current status of the background service"""
    try:
        # Check if service has processed any screenshots today
        file_manager = st.session_state.processors['file_manager']
        today_files = file_manager.get_recent_files(days=1)
        
        # Count screenshots taken today
        screenshot_count = len([f for f in today_files if f.suffix == '.png'])
        
        # Get uptime
        uptime = datetime.now() - st.session_state.background_service_start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Get last screenshot time
        last_screenshot_time = None
        if today_files:
            png_files = [f for f in today_files if f.suffix == '.png']
            if png_files:
                latest_file = max(png_files, key=lambda x: x.stat().st_mtime)
                last_screenshot_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
        
        return {
            'running': True,  # Always true when Streamlit is running with background service
            'uptime': uptime_str,
            'screenshot_count': screenshot_count,
            'last_screenshot_time': last_screenshot_time,
            'hotkeys_active': True  # Background service handles this
        }
    except Exception as e:
        return {
            'running': False,
            'error': str(e)
        }


def check_for_new_screenshots():
    """Check for new screenshots and load the latest one"""
    try:
        file_manager = st.session_state.processors['file_manager']
        recent_files = file_manager.get_recent_files(days=1)
        
        if recent_files:
            # Get the most recent screenshot
            latest_file = max(recent_files, key=lambda x: x.stat().st_mtime)
            latest_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
            
            # Check if it's newer than our last check
            if latest_time > st.session_state.last_check_time:
                # Try to find corresponding image
                image_path = latest_file.with_suffix('.png')
                if image_path.exists() and str(image_path) != st.session_state.auto_loaded_screenshot:
                    st.session_state.current_image_path = str(image_path)
                    st.session_state.current_image = Image.open(image_path)
                    st.session_state.auto_loaded_screenshot = str(image_path)
                    st.session_state.last_check_time = datetime.now()
                    # Update screenshot count
                    status = get_background_service_status()
                    st.session_state.last_screenshot_count = status['screenshot_count']
                    return True
                    
        st.session_state.last_check_time = datetime.now()
        return False
    except Exception as e:
        st.error(f"Error checking for new screenshots: {e}")
        return False


async def process_with_ai_chat(message, image_path=None, provider=None, model=None):
    """Process message with AI chat"""
    try:
        chat_processor = get_ai_chat_processor(provider, model)
        if not chat_processor:
            return "AI chat not available. Please check your configuration and API keys."
        
        # Prepare context
        context = {
            'image_path': image_path,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add OCR text if image is available
        if image_path:
            ocr_processor = st.session_state.processors['ocr']
            context['ocr_text'] = ocr_processor.extract_text(image_path)
            
            # Add VLM description if available
            vlm_processor = st.session_state.processors['vlm']
            if vlm_processor.is_available():
                context['vlm_description'] = vlm_processor.describe_image(image_path)
        
        response = await chat_processor.process_message(message, context)
        return response
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    st.set_page_config(
        page_title="SnapMark - Screenshot & AI Tool",
        page_icon="📸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    
    # Auto-refresh to detect new screenshots
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh for new screenshots", value=True, 
                                      help="Automatically loads new screenshots taken with hotkeys")
    
    if auto_refresh:
        # Check for new screenshots
        if check_for_new_screenshots():
            st.sidebar.success("🆕 New screenshot loaded!")
            st.rerun()
        
        # Auto-refresh every few seconds
        import time
        time.sleep(3)  # Check every 3 seconds
        st.rerun()
    
    st.title("📸 SnapMark - Screenshot & AI Tool")
    
    # Show hotkey info
    with st.expander("ℹ️ Global Hotkey Information", expanded=False):
        st.info("""
        **Global Screenshot Hotkeys:**
        - **macOS**: Cmd+Shift+3
        - **Windows/Linux**: Ctrl+Shift+3
        
        When you run `uv run snapmark streamlit`, a background service automatically starts to handle global hotkeys.
        Screenshots taken with hotkeys will automatically appear in this interface if auto-refresh is enabled.
        
        Alternatively, you can use the "Take Screenshot" button below.
        """)
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Background Service Status
        st.subheader("🔧 Background Service")
        status = get_background_service_status()
        
        if status.get('running'):
            # Service status indicator
            col1, col2 = st.columns([1, 3])
            with col1:
                st.success("🟢 Active")
            with col2:
                st.text(f"Uptime: {status['uptime']}")
            
            # Hotkey status
            if status['hotkeys_active']:
                st.info("⌨️ **Hotkeys Active**\n- macOS: `Cmd+Shift+3`\n- Win/Linux: `Ctrl+Shift+3`")
            
            # Screenshot stats
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📸 Screenshots Today", status['screenshot_count'], 
                         delta=status['screenshot_count'] - st.session_state.last_screenshot_count if status['screenshot_count'] != st.session_state.last_screenshot_count else None)
            with col2:
                # Show processing indicator if new screenshot detected
                if status['last_screenshot_time'] and (datetime.now() - status['last_screenshot_time']).total_seconds() < 5:
                    st.caption("🔄 Processing...")
            
            # Last screenshot time
            if status['last_screenshot_time']:
                time_ago = datetime.now() - status['last_screenshot_time']
                if time_ago.total_seconds() < 60:
                    time_str = f"{int(time_ago.total_seconds())} seconds ago"
                elif time_ago.total_seconds() < 3600:
                    time_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
                else:
                    time_str = f"{int(time_ago.total_seconds() / 3600)} hours ago"
                st.caption(f"Last screenshot: {time_str}")
            else:
                st.caption("No screenshots taken yet")
        else:
            st.error(f"🔴 Service Error: {status.get('error', 'Unknown')}")
        
        st.divider()
        
        # Model selection
        st.subheader("🤖 AI Model")
        
        # Check available API keys first - fallback to VLM keys if ai_chat keys not set
        openai_key = (st.session_state.config.get("ai_chat.openai_api_key") or 
                     st.session_state.config.get("vlm.openai_api_key") or 
                     os.getenv("OPENAI_API_KEY"))
        claude_key = (st.session_state.config.get("ai_chat.claude_api_key") or 
                     os.getenv("ANTHROPIC_API_KEY"))
        gemini_key = (st.session_state.config.get("ai_chat.gemini_api_key") or 
                     os.getenv("GOOGLE_API_KEY"))
        
        # Build model options based on available keys
        model_options = ["demo-mode"]
        if openai_key:
            model_options.extend(["gpt-4o-mini", "gpt-4o"])
        if claude_key:
            model_options.append("claude-3-5-sonnet-20241022")
        if gemini_key:
            model_options.append("gemini-1.5-pro")
        model_options.append("local-model")  # Always available for Ollama
        
        # Auto-select first available model if not demo mode
        default_index = 1 if len(model_options) > 1 and openai_key else 0
        
        selected_model = st.selectbox("Select Model", model_options, 
                                     index=default_index,
                                     help="Models shown based on available API keys")
        
        # Show API key status
        if selected_model != "demo-mode":
            provider = None
            if selected_model.startswith(("gpt", "o1")):
                provider = "openai"
                api_key = openai_key
            elif selected_model.startswith("claude"):
                provider = "claude"
                api_key = claude_key
            elif selected_model.startswith("gemini"):
                provider = "gemini"
                api_key = gemini_key
            else:
                provider = "ollama"
                api_key = "localhost"
            
            if api_key and api_key != "localhost":
                # Show where the key is coming from
                key_source = "environment"
                if st.session_state.config.get("ai_chat.openai_api_key"):
                    key_source = "ai_chat config"
                elif st.session_state.config.get("vlm.openai_api_key"):
                    key_source = "vlm config"
                st.success(f"✅ {provider.upper()} API key configured ({key_source})")
            elif provider == "ollama":
                st.info("📡 Using Ollama (local model)")
            else:
                st.warning(f"⚠️ {provider.upper()} API key not found")
        else:
            st.info("🎭 Demo mode selected - no real AI processing")
        
        # Path settings
        st.subheader("📁 Paths")
        snapmark_dir = st.session_state.config.get_snapmark_dir()
        markdown_output_path = st.text_input(
            "Markdown Output Path", 
            value=str(snapmark_dir)
        )
        screenshot_save_path = st.text_input(
            "Screenshot Save Path", 
            value=str(snapmark_dir)
        )
        
        # Hotkey settings
        st.subheader("⌨️ Hotkeys")
        hotkey_enabled = st.checkbox("Enable Global Hotkeys", value=True)
        hotkey_combination = st.text_input("Hotkey Combination", value="cmd+shift+3")
        
        # Summary settings
        st.subheader("📄 Summary")
        summary_format = st.selectbox("Output Format", ["Markdown", "PDF"])
        
    # Main layout - two columns
    col1, col2 = st.columns([1, 1])
    
    # Left column - Chat interface
    with col1:
        st.header("💬 AI Chat")
        
        # Chat messages display
        chat_container = st.container(height=400)
        with chat_container:
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask AI about the screenshot or anything else..."):
            # Add user message to chat history
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
            
            # Process with AI
            with st.spinner("Thinking..."):
                try:
                    # Handle demo mode
                    if selected_model == "demo-mode":
                        response = f"🤖 **Demo Mode Response**\n\nYou asked: '{prompt}'\n\nThis is a demo response. In real mode, I would:\n- Analyze your screenshot using OCR\n- Process the image with VLM if available\n- Provide AI-powered insights\n- Answer questions about the content\n\nTo use real AI features, please:\n1. Set up API keys for your preferred provider\n2. Select a real model from the dropdown\n3. Try your question again!"
                    else:
                        # Determine provider from selected model
                        provider = None
                        if selected_model.startswith(("gpt", "o1")):
                            provider = "openai"
                        elif selected_model.startswith("claude"):
                            provider = "claude"
                        elif selected_model.startswith("gemini"):
                            provider = "gemini"
                        else:
                            provider = "ollama"
                        
                        # Use asyncio to run the async function
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        response = loop.run_until_complete(
                            process_with_ai_chat(prompt, st.session_state.current_image_path, provider, selected_model)
                        )
                        loop.close()
                    
                    # Add AI response to chat history
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    
                    # Display AI response
                    with chat_container:
                        with st.chat_message("assistant"):
                            st.markdown(response)
                            
                except Exception as e:
                    st.error(f"Error processing message: {str(e)}")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            st.rerun()
    
    # Right column - Screenshot display and tools
    with col2:
        st.header("🖼️ Screenshot")
        
        # Screenshot controls
        col2_1, col2_2, col2_3 = st.columns(3)
        
        with col2_1:
            if st.button("📸 Take Screenshot", type="primary"):
                try:
                    with st.spinner("Taking screenshot..."):
                        capture = st.session_state.processors['capture']
                        image_path = capture.capture_screen()
                        st.session_state.current_image_path = image_path
                        st.session_state.current_image = Image.open(image_path)
                        st.success(f"Screenshot saved: {Path(image_path).name}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error taking screenshot: {str(e)}")
        
        with col2_2:
            if st.button("📋 Copy Image") and st.session_state.current_image_path:
                try:
                    copy_image_to_clipboard(st.session_state.current_image_path)
                    st.success("Image copied to clipboard!")
                except Exception as e:
                    st.error(f"Error copying image: {str(e)}")
        
        with col2_3:
            annotation_mode = st.checkbox("🔴 Red Frame Tool")
        
        # Image display
        if st.session_state.current_image:
            st.image(
                st.session_state.current_image, 
                caption="Current Screenshot", 
                use_container_width=True
            )
            
            # Red frame annotation tool
            if annotation_mode:
                st.subheader("🔴 Add Red Frame")
                col_x1, col_y1, col_x2, col_y2 = st.columns(4)
                with col_x1:
                    x1 = st.number_input("X1", min_value=0, value=50)
                with col_y1:
                    y1 = st.number_input("Y1", min_value=0, value=50)
                with col_x2:
                    x2 = st.number_input("X2", min_value=0, value=150)
                with col_y2:
                    y2 = st.number_input("Y2", min_value=0, value=150)
                
                if st.button("Add Frame"):
                    try:
                        annotated_path = add_red_frame_annotation(
                            st.session_state.current_image_path, x1, y1, x2, y2
                        )
                        st.session_state.current_image_path = annotated_path
                        st.session_state.current_image = Image.open(annotated_path)
                        st.success("Red frame added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding frame: {str(e)}")
        else:
            st.info("No screenshot available. Click 'Take Screenshot' to capture your screen.")
    
    # Summary section at the bottom
    st.header("📄 Summary Generation")
    
    col_summary_1, col_summary_2 = st.columns([3, 1])
    
    with col_summary_1:
        summary_prompt = st.text_area(
            "Summary Prompt", 
            placeholder="Enter a prompt to generate a summary of all markdown files and screenshots...",
            height=100
        )
    
    with col_summary_2:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("📊 Generate Summary", type="primary"):
            if summary_prompt:
                try:
                    with st.spinner("Generating summary..."):
                        ai_summary = st.session_state.processors['ai_summary']
                        file_manager = st.session_state.processors['file_manager']
                        
                        # Get recent files
                        recent_files = file_manager.get_recent_files(days=7)  # Last 7 days
                        
                        if not recent_files:
                            st.warning("No recent files found to summarize.")
                        else:
                            # Read file contents
                            note_contents = []
                            for file_path in recent_files:
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    note_contents.append(content)
                                except Exception as e:
                                    st.warning(f"Could not read {file_path}: {str(e)}")
                            
                            if note_contents:
                                # Generate summary with custom prompt
                                summary = ai_summary.generate_summary_with_prompt(
                                    note_contents, summary_prompt
                                )
                                
                                # Display summary
                                st.subheader("📊 Generated Summary")
                                # Store the summary in session state
                                st.session_state['last_summary'] = summary
                                st.session_state['last_summary_prompt'] = summary_prompt
                                st.session_state['last_summary_time'] = datetime.now()
                                
                                # Save summary option
                                if summary_format == "PDF":
                                    # TODO: Implement PDF export
                                    st.info("PDF export not yet implemented. Summary shown below.")
                                else:
                                    # Save as markdown
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    summary_path = Path(markdown_output_path) / f"summary_{timestamp}.md"
                                    
                                    with open(summary_path, 'w', encoding='utf-8') as f:
                                        f.write(f"# Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                                        f.write(f"**Prompt:** {summary_prompt}\n\n")
                                        f.write(summary)
                                    
                                    st.success(f"Summary saved to: {summary_path}")
                                
                                # Display the generated summary below
                                st.rerun()
                            else:
                                st.error("No valid file contents found to summarize.")
                        
                except Exception as e:
                    st.error(f"Error generating summary: {str(e)}")
            else:
                st.warning("Please enter a summary prompt.")
    
    # Display generated insights below the prompt
    if 'last_summary' in st.session_state and st.session_state.get('last_summary'):
        st.divider()
        
        # Show generated insights
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader("📊 Generated Insights")
        with col2:
            if st.button("🗑️ Clear", key="clear_summary"):
                st.session_state['last_summary'] = None
                st.session_state['last_summary_prompt'] = None
                st.session_state['last_summary_time'] = None
                st.rerun()
        
        # Show metadata
        if 'last_summary_time' in st.session_state:
            time_ago = datetime.now() - st.session_state['last_summary_time']
            if time_ago.total_seconds() < 60:
                time_str = "just now"
            elif time_ago.total_seconds() < 3600:
                time_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
            else:
                time_str = f"{int(time_ago.total_seconds() / 3600)} hours ago"
            
            st.caption(f"Generated {time_str} | Prompt: *{st.session_state.get('last_summary_prompt', 'N/A')}*")
        
        # Display the summary content
        with st.container():
            st.markdown(st.session_state['last_summary'])
            
            # Copy button for the summary
            if st.button("📋 Copy to Clipboard", key="copy_summary"):
                # Note: Streamlit doesn't have native clipboard support
                # We'll show the text in a code block for easy copying
                st.code(st.session_state['last_summary'], language="markdown")
                st.info("Select the text above and copy it manually (Ctrl+C or Cmd+C)")
    
    # Background Service Activity Log
    with st.expander("🔧 Background Service Activity", expanded=False):
        try:
            # Get recent activity
            file_manager = st.session_state.processors['file_manager']
            recent_files = file_manager.get_recent_files(days=1)
            
            if recent_files:
                # Group files by screenshot session
                sessions = {}
                for file in sorted(recent_files, key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
                    # Extract timestamp from filename
                    stem = file.stem
                    if '_' in stem:
                        timestamp_str = stem.split('_', 1)[1]  # After 'screen_'
                        sessions.setdefault(timestamp_str, []).append(file)
                
                # Display sessions
                for timestamp, files in list(sessions.items())[:5]:  # Show last 5 sessions
                    # Find the PNG file for this session
                    png_file = next((f for f in files if f.suffix == '.png'), None)
                    if png_file:
                        col1, col2, col3 = st.columns([2, 3, 1])
                        with col1:
                            time_str = datetime.fromtimestamp(png_file.stat().st_mtime).strftime('%H:%M:%S')
                            st.text(f"📸 {time_str}")
                        with col2:
                            # Show what was processed
                            processed = []
                            if any(f.suffix == '.md' for f in files):
                                processed.append("📝 Markdown")
                            if any('.xlsx' in f.name for f in files):
                                processed.append("📊 Excel")
                            st.caption(" • ".join(processed) if processed else "Processing...")
                        with col3:
                            if st.button("Load", key=f"load_bg_{timestamp}"):
                                st.session_state.current_image_path = str(png_file)
                                st.session_state.current_image = Image.open(png_file)
                                st.rerun()
            else:
                st.info("No background service activity today")
                
        except Exception as e:
            st.error(f"Error loading activity: {str(e)}")
    
    # Recent screenshots list
    with st.expander("📋 Recent Screenshots", expanded=False):
        try:
            file_manager = st.session_state.processors['file_manager']
            recent_files = file_manager.get_recent_files(days=1)
            
            if recent_files:
                for file_path in recent_files[:10]:  # Show last 10
                    col_file_1, col_file_2 = st.columns([3, 1])
                    with col_file_1:
                        st.text(f"📄 {file_path.name}")
                        st.caption(f"Modified: {datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
                    with col_file_2:
                        if st.button(f"Load", key=f"load_{file_path.name}"):
                            # Try to find corresponding image
                            image_path = file_path.with_suffix('.png')
                            if image_path.exists():
                                st.session_state.current_image_path = str(image_path)
                                st.session_state.current_image = Image.open(image_path)
                                st.rerun()
                            else:
                                st.warning("Associated image not found.")
            else:
                st.info("No recent screenshots found.")
        except Exception as e:
            st.error(f"Error loading recent files: {str(e)}")


if __name__ == "__main__":
    main()