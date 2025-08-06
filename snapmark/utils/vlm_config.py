import json
from pathlib import Path
from typing import Optional


def switch_vlm_provider(provider: str, model: Optional[str] = None, api_key: Optional[str] = None):
    """
    Switch between VLM providers (OpenAI or Ollama)
    
    Args:
        provider: 'openai' or 'ollama'
        model: Model name (e.g., 'gpt-4o' for OpenAI, 'llama3.2-vision' for Ollama)
        api_key: API key for OpenAI (optional, can be set via environment variable)
    """
    config_path = Path.home() / '.snapmark2' / 'config.json'
    
    # Load existing config
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Ensure vlm section exists
    if 'vlm' not in config:
        config['vlm'] = {}
    
    # Update provider
    config['vlm']['provider'] = provider
    config['vlm']['enabled'] = True
    
    # Set provider-specific settings
    if provider == 'openai':
        if model:
            config['vlm']['openai_model'] = model
        if api_key:
            config['vlm']['openai_api_key'] = api_key
        print(f"Switched to OpenAI with model: {model or config['vlm'].get('openai_model', 'gpt-4o')}")
    elif provider == 'ollama':
        if model:
            config['vlm']['ollama_model'] = model
            config['vlm']['model'] = model  # For backward compatibility
        print(f"Switched to Ollama with model: {model or config['vlm'].get('ollama_model', 'llama3.2-vision')}")
    else:
        print(f"Unknown provider: {provider}. Use 'openai' or 'ollama'")
        return
    
    # Save config
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuration saved to {config_path}")


def get_vlm_status():
    """Get current VLM provider status"""
    from ..core.vlm import VLMProcessor
    from ..config import config
    
    provider = config.get('vlm.provider', 'ollama')
    enabled = config.get('vlm.enabled', False)
    
    if not enabled:
        print("VLM is currently disabled")
        return
    
    print(f"Current VLM Provider: {provider}")
    
    if provider == 'openai':
        model = config.get('vlm.openai_model', 'gpt-4o')
        api_key = config.get('vlm.openai_api_key', '')
        print(f"OpenAI Model: {model}")
        print(f"API Key: {'Set' if api_key else 'Not set (check OPENAI_API_KEY env var)'}")
    elif provider == 'ollama':
        model = config.get('vlm.ollama_model', config.get('vlm.model', 'llama3.2-vision'))
        api_url = config.get('vlm.api_url', 'http://localhost:11434')
        print(f"Ollama Model: {model}")
        print(f"API URL: {api_url}")
        
        # Check if Ollama is running
        vlm = VLMProcessor()
        if vlm.is_available():
            print(f"Status: ✓ Available")
            # List available models
            models = VLMProcessor.list_available_models('ollama', api_url)
            if models:
                print(f"Available Ollama models: {', '.join(models)}")
        else:
            print(f"Status: ✗ Not available (make sure Ollama is running)")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m snapmark.utils.vlm_config status")
        print("  python -m snapmark.utils.vlm_config switch <provider> [model] [api_key]")
        print("\nExamples:")
        print("  python -m snapmark.utils.vlm_config switch openai gpt-4o")
        print("  python -m snapmark.utils.vlm_config switch ollama llama3.2-vision")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        get_vlm_status()
    elif command == "switch":
        if len(sys.argv) < 3:
            print("Error: Provider required")
            sys.exit(1)
        provider = sys.argv[2]
        model = sys.argv[3] if len(sys.argv) > 3 else None
        api_key = sys.argv[4] if len(sys.argv) > 4 else None
        switch_vlm_provider(provider, model, api_key)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)