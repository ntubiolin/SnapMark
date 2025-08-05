# SnapMark 🚀

A powerful desktop screenshot tool with OCR, AI chat, and Markdown generation capabilities. Built with Python and features both PyQt6 and Streamlit interfaces.

## Features

### Core Features
- 📸 **Screenshot Capture**: Hotkey-triggered screenshots (Cmd+Shift+3)
- 🔍 **OCR Processing**: Automatic text extraction from screenshots using Tesseract
- 🖼️ **VLM Image Description**: AI-powered image descriptions using Vision Language Models (optional)
- 📝 **Markdown Generation**: Auto-creates organized notes with timestamps and metadata
- 📁 **Smart Organization**: Automatic file organization by date
- ⌨️ **CLI Support**: Command-line interface for all functions

### Enhanced UI Features
- 🤖 **AI Chat Interface**: Interactive chat with AI models (GPT, Claude, Gemini, Ollama)
- 🖼️ **Screenshot Display**: Visual display of captured screenshots with annotation support
- 🔴 **Red Box Annotation**: Click and drag to add red boxes for highlighting important areas
- 📋 **Copy to Clipboard**: Copy screenshots (with annotations) directly to clipboard
- ⚙️ **Model Selection**: Choose from multiple AI models (GPT-4, Claude, Gemini, etc.)
- 📂 **Path Configuration**: Customizable output directory for screenshots and notes
- 📄 **Summary Reports**: Generate comprehensive reports from multiple notes with custom prompts
- 🖥️ **Dual Interface**: Choose between PyQt6 desktop app or Streamlit web interface
- 🔍 **Advanced Search**: Full-text search with tags and date filtering

## Installation

### Prerequisites

1. **Tesseract OCR**: Required for text extraction
   ```bash
   # macOS
   brew install tesseract tesseract-lang
   
   # Ubuntu/Debian
   sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra
   
   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

2. **Python 3.8+**: Required for the application

3. **VLM Provider (Optional)**: Required for AI-powered image descriptions
   - **Ollama** (Local, Free):
     ```bash
     # Install Ollama from https://ollama.ai
     # Then install the Gemma 3n model
     ollama pull gemma3n:e4b
     ```
   - **OpenAI** (Cloud, Paid): Requires API key
   - **Azure OpenAI** (Cloud, Paid): Requires API key and endpoint

### Install SnapMark

```bash
# Clone the repository
git clone <repository-url>
cd SnapMark

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Usage

### GUI Interfaces

SnapMark offers two modern interface options:

#### PyQt6 Desktop GUI (Default)

The PyQt6 GUI provides a native desktop experience:

```bash
# Launch the PyQt6 desktop GUI (default)
snapmark

# Or explicitly
snapmark gui
```

#### Streamlit Web Interface

The Streamlit interface provides a modern web-based experience:

```bash
# Launch the Streamlit web interface
snapmark streamlit

# Or use the GUI command with --streamlit flag
snapmark gui --streamlit
```

The Streamlit interface will be available at `http://localhost:8501` in your web browser.

#### Key UI Components (Both Interfaces):

1. **Left Panel - AI Chat Interface**:
   - Interactive chat with multiple AI models
   - Supports text and image inputs
   - Conversation history maintained during session
   - Context-aware responses with OCR and VLM data

2. **Right Panel - Screenshot Display & Controls**:
   - Visual display of captured screenshots
   - Red box annotation tool for highlighting
   - Copy to clipboard functionality
   - Screenshot capture button

3. **Settings Panel**:
   - **Model Selection**: Choose from GPT-4, Claude, Gemini, and other models
   - **Path Configuration**: Set custom output directory for screenshots and markdown
   - **Summary Generation**: Create reports with custom prompts from multiple notes
   - **Hotkey Configuration**: Enable/disable global hotkeys

#### AI Models Supported:
- **OpenAI**: gpt-4o, gpt-4o-mini, o1-preview, o1-mini
- **Anthropic**: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
- **Google**: gemini-1.5-pro, gemini-1.5-flash
- **Ollama**: Local models (requires Ollama installation)

#### Usage Workflow:
1. Launch either PyQt6 desktop GUI or Streamlit web interface
2. Press **Cmd+Shift+3** (or use the capture button) to take a screenshot
3. Screenshot appears in the right panel automatically with OCR text extracted
4. Chat with AI about the screenshot in the left panel (AI can see OCR and image description)
5. Use annotation tools to highlight important areas with red frames
6. Copy annotated screenshot to clipboard if needed
7. Generate summary reports from multiple screenshots using custom prompts

### Background Service

```bash
# Start background service with global hotkeys
snapmark background

# Start background service with custom output directory
snapmark background --output /path/to/custom/directory

# Or use the dedicated background command
snapmark-bg
```

The background service runs continuously and provides:
- **Global hotkeys** for system-wide screenshot capture
- **Silent operation** in system tray
- **Automatic processing** of screenshots (OCR + markdown generation)
- **Cross-platform support** for hotkeys

### CLI Mode

```bash
# Take a screenshot
snapmark screenshot

# Take a screenshot of specific region
snapmark screenshot --region 100,100,800,600

# Take a screenshot with VLM image description
snapmark screenshot --vlm

# Take a screenshot and process with MCP servers
snapmark screenshot --mcp

# Take a screenshot with both VLM and MCP processing
snapmark screenshot --vlm --mcp

# Search notes
snapmark search "meeting notes"
snapmark search "project" --tags work urgent --limit 5

# Generate summary
snapmark summary --days 7 --output weekly_summary.md

# Rebuild search index
snapmark index

# Generate VLM description for existing image
snapmark vlm path/to/image.png

# Extract action items from image using VLM
snapmark vlm path/to/image.png --action-items

# Extract key information from image using VLM
snapmark vlm path/to/image.png --key-info

# Use custom prompt for image description
snapmark vlm path/to/image.png --prompt "Describe the user interface elements in this screenshot"

# List configured MCP servers
snapmark mcp list

# Test MCP server connection
snapmark mcp test excel

# Process existing image with MCP servers
snapmark mcp process path/to/image.png --markdown path/to/note.md
```

## Configuration

SnapMark creates a configuration file at `~/.snapmark2/config.json`:

```json
{
  "output_directory": "SnapMarkData",
  "ocr_language": "eng+chi_tra+chi_sim",
  "hotkeys": {
    "screenshot": "cmd+shift+3"
  },
  "ai_summary": {
    "enabled": false,
    "daily_time": "18:00"
  },
  "vlm": {
    "enabled": false,
    "provider": "ollama",
    "model": "gemma3n:e4b",
    "api_url": "http://localhost:11434",
    "openai_api_key": "",
    "openai_model": "gpt-4-vision-preview",
    "azure_api_key": "",
    "azure_endpoint": "",
    "azure_api_version": "2024-02-01",
    "azure_model": "gpt-4-vision"
  },
  "mcp": {
    "enabled": false,
    "servers": {
      "excel": {
        "enabled": false,
        "command": "uvx",
        "args": ["excel-mcp-server", "stdio"],
        "env": {
          "EXCEL_FILES_PATH": "./SnapMarkData/exports"
        }
      }
    }
  }
}
```

### AI Features (Optional)

#### AI Chat & Summaries
To enable AI chat and summary features, configure the appropriate API keys:

##### OpenAI Models
```bash
export OPENAI_API_KEY="your-api-key-here"
```

##### Anthropic Claude Models
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

##### Google Gemini Models
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

##### Azure OpenAI Models
```bash
export AZURE_OPENAI_API_KEY="your-api-key-here"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
```

You can also configure these in the `~/.snapmark2/config.json` file:

```json
{
  "ai_chat": {
    "openai_api_key": "your-openai-key",
    "claude_api_key": "your-claude-key", 
    "gemini_api_key": "your-gemini-key",
    "azure_api_key": "your-azure-key",
    "azure_endpoint": "https://your-resource.openai.azure.com/",
    "azure_api_version": "2024-02-01"
  }
}
```

**Note**: If you already have OpenAI API keys configured for VLM features under the `vlm` section, the AI chat will automatically use those keys as a fallback:

```json
{
  "vlm": {
    "openai_api_key": "your-openai-key",
    "azure_api_key": "your-azure-key",
    "azure_endpoint": "https://your-resource.openai.azure.com/"
  }
}
```

#### VLM Image Descriptions
SnapMark supports multiple VLM providers for AI-powered image descriptions:

##### Option 1: Ollama (Local, Free)
1. Install and start Ollama:
   ```bash
   # Install Ollama from https://ollama.ai
   ollama serve
   ```

2. Install the Gemma 3n model:
   ```bash
   ollama pull gemma3n:e4b
   ```

3. Configure in `~/.snapmark2/config.json`:
   ```json
   "vlm": {
     "enabled": true,
     "provider": "ollama",
     "model": "gemma3n:e4b",
     "api_url": "http://localhost:11434"
   }
   ```

##### Option 2: OpenAI (Cloud, Paid)
1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. Configure in `~/.snapmark2/config.json`:
   ```json
   "vlm": {
     "enabled": true,
     "provider": "openai",
     "openai_model": "gpt-4-vision-preview"
   }
   ```

##### Option 3: Azure OpenAI (Cloud, Paid)
1. Set your Azure OpenAI credentials:
   ```bash
   export AZURE_OPENAI_API_KEY="your-api-key-here"
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   ```

2. Configure in `~/.snapmark2/config.json`:
   ```json
   "vlm": {
     "enabled": true,
     "provider": "azure_openai",
     "azure_endpoint": "https://your-resource.openai.azure.com/",
     "azure_model": "gpt-4-vision",
     "azure_api_version": "2024-02-01"
   }
   ```

You can also use the `--vlm` flag with screenshot commands to enable VLM processing temporarily.

#### MCP (Model Context Protocol) Integration
SnapMark supports MCP servers for post-processing screenshot data. This allows integration with various external tools and services.

##### Setting up MCP Servers

1. **Install MCP dependencies**:
   ```bash
   uv add "mcp>=1.0.0"
   ```

2. **Configure MCP servers** in `~/.snapmark2/config.json`:
   ```json
   "mcp": {
     "enabled": true,
     "servers": {
       "excel": {
         "enabled": true,
         "command": "uvx",
         "args": ["excel-mcp-server", "stdio"],
         "env": {
           "EXCEL_FILES_PATH": "./SnapMarkData/exports"
         }
       },
       "custom": {
         "enabled": true,
         "command": "python",
         "args": ["path/to/custom_mcp_server.py"],
         "env": {
           "CUSTOM_CONFIG": "value"
         }
       }
     }
   }
   ```

##### Excel MCP Server Example

1. **Install excel-mcp-server**:
   ```bash
   uvx install excel-mcp-server
   ```

2. **Enable in configuration**:
   ```json
   "mcp": {
     "enabled": true,
     "servers": {
       "excel": {
         "enabled": true,
         "command": "uvx",
         "args": ["excel-mcp-server", "stdio"],
         "env": {
           "EXCEL_FILES_PATH": "./SnapMarkData/exports"
         }
       }
     }
   }
   ```

3. **Create exports directory**:
   ```bash
   mkdir -p SnapMarkData/exports
   ```

##### MCP Usage

**Automatic Processing**: When MCP is enabled, screenshot data is automatically sent to configured servers after OCR and VLM processing.

**Manual Processing**:
```bash
# List configured servers
snapmark mcp list

# Test server connectivity
snapmark mcp test excel

# Process existing screenshot
snapmark mcp process screenshot.png --markdown screenshot.md
```

**CLI Integration**:
```bash
# Process screenshot with MCP servers
snapmark screenshot --mcp

# Combined VLM and MCP processing
snapmark screenshot --vlm --mcp
```

## File Organization

Screenshots and notes are organized by date:

```
SnapMarkData/
├── 2025/
│   └── 08/
│       └── 04/
│           ├── screen_14-25-12.png
│           ├── screen_14-25-12.md
│           └── daily_summary_2025-08-04.md
└── weekly_summaries/
    └── weekly_summary_2025-W31.md
```

## Hotkeys

- **Cmd+Shift+3** (macOS): Take screenshot
- **Ctrl+Shift+3** (Linux/Windows): Take screenshot

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
pytest

# Format code
black snapmark/

# Type checking
mypy snapmark/
```

## Features Overview

### Screenshot Module
- Cross-platform screenshot capture
- Hotkey support
- Region and full-screen capture
- Automatic file naming with timestamps

### OCR Processing
- Multi-language support (English, Chinese Traditional/Simplified)
- Confidence scoring
- Error handling and fallbacks

### Markdown Generation
- Template-based note creation
- Metadata insertion (tags, timestamps)
- Image embedding
- OCR text inclusion

### AI Integration
- Daily summary generation
- Weekly reports
- Action item extraction
- Scheduled processing

### Search & Management
- SQLite-based indexing
- Full-text search
- Tag filtering
- Date range queries
- Storage statistics

## System Requirements

- **OS**: macOS 10.14+, Ubuntu 18.04+, Windows 10+
- **Python**: 3.8 or higher
- **Memory**: 512MB RAM minimum
- **Storage**: Varies based on screenshot volume

## Troubleshooting

### Common Issues

1. **Tesseract not found**
   - Ensure Tesseract is installed and in PATH
   - On macOS: `brew install tesseract`

2. **Hotkeys not working**
   - Check system permissions for accessibility
   - Try running with administrator privileges

3. **OCR accuracy issues**
   - Install additional language packs
   - Ensure good image quality

4. **AI features not working**
   - Verify OpenAI API key is set
   - Check internet connection

5. **VLM features not working**
   - **Ollama**: Ensure Ollama is running (`ollama serve`) and model is installed (`ollama list`)
   - **OpenAI**: Verify OPENAI_API_KEY environment variable is set
   - **Azure OpenAI**: Verify AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are set
   - Check VLM is enabled in config or use `--vlm` flag
   - Verify the correct provider is configured in config.json

6. **MCP features not working**
   - Verify MCP is enabled in config: `"mcp": {"enabled": true}`
   - Check server configurations and paths are correct
   - Test server connectivity: `snapmark mcp test server_name`
   - Ensure required MCP server packages are installed (e.g., `uvx install excel-mcp-server`)
   - Check server environment variables are properly set
   - Verify server command and arguments are correct

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Roadmap

- [ ] Plugin system for custom processors
- [ ] Cloud storage integration
- [ ] Mobile companion app
- [ ] Advanced OCR models
- [ ] Collaborative features
- [ ] Export to various formats (PDF, HTML, etc.)