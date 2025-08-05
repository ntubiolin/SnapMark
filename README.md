# SnapMark2 🚀

A powerful desktop screenshot tool with OCR and Markdown generation capabilities. Built with Python and PyQt5.

## Features

- 📸 **Screenshot Capture**: Hotkey-triggered screenshots (Cmd+Shift+3)
- 🔍 **OCR Processing**: Automatic text extraction from screenshots using Tesseract
- 🖼️ **VLM Image Description**: AI-powered image descriptions using Vision Language Models (optional)
- 📝 **Markdown Generation**: Auto-creates organized notes with timestamps and metadata
- 🤖 **AI Summaries**: Generate daily/weekly summaries using OpenAI (optional)
- 🔍 **Advanced Search**: Full-text search with tags and date filtering
- 🖥️ **Modern GUI**: Clean PyQt5 interface with system tray support
- 📁 **Smart Organization**: Automatic file organization by date
- ⌨️ **CLI Support**: Command-line interface for all functions

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

### Install SnapMark2

```bash
# Clone the repository
git clone <repository-url>
cd SnapMark2

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Usage

### GUI Mode (Default)

```bash
# Launch the GUI application
snapmark

# Or explicitly
snapmark gui
```

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
```

## Configuration

SnapMark2 creates a configuration file at `~/.snapmark2/config.json`:

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
  }
}
```

### AI Features (Optional)

#### OpenAI Summaries
To enable AI summaries, set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

#### VLM Image Descriptions
SnapMark2 supports multiple VLM providers for AI-powered image descriptions:

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