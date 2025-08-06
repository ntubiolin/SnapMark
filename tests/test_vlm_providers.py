#!/usr/bin/env python3
"""
Test script to verify VLM providers (OpenAI and Ollama) work correctly
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from snapmark.core.vlm import VLMProcessor, VLMProvider
from snapmark.config import config


def test_provider(provider_name: str, model: str = None):
    """Test a specific VLM provider"""
    print(f"\n{'='*50}")
    print(f"Testing {provider_name} Provider")
    print('='*50)
    
    try:
        # Create VLM processor with specific provider
        vlm = VLMProcessor(provider=provider_name, model=model)
        
        # Get provider info
        info = vlm.get_provider_info()
        print(f"Provider: {info['provider']}")
        print(f"Model: {info['model']}")
        if info.get('api_url'):
            print(f"API URL: {info['api_url']}")
        
        # Check availability
        if vlm.is_available():
            print(f"Status: ✓ Available")
            
            # Test with a sample image if provided
            test_image = "test_image.png"
            if Path(test_image).exists():
                print(f"\nTesting with {test_image}...")
                result = vlm.describe_image(test_image, "Describe this image briefly in one sentence.")
                print(f"Result: {result[:200]}...")
            else:
                print(f"\nNo test image found. Create {test_image} to test image description.")
        else:
            print(f"Status: ✗ Not available")
            if provider_name == 'ollama':
                print("Make sure Ollama is running: ollama serve")
                print("And pull a vision model: ollama pull llama3.2-vision")
            elif provider_name == 'openai':
                print("Make sure OPENAI_API_KEY is set or configured in config.json")
                
    except Exception as e:
        print(f"Error: {e}")


def list_ollama_models():
    """List available Ollama models"""
    print("\nAvailable Ollama models:")
    models = VLMProcessor.list_available_models('ollama')
    if models:
        vision_models = [m for m in models if 'vision' in m.lower() or 'llava' in m.lower()]
        if vision_models:
            print("Vision models:")
            for model in vision_models:
                print(f"  - {model}")
        other_models = [m for m in models if m not in vision_models]
        if other_models:
            print("Other models (may not support vision):")
            for model in other_models[:5]:  # Show only first 5
                print(f"  - {model}")
            if len(other_models) > 5:
                print(f"  ... and {len(other_models) - 5} more")
    else:
        print("No models found. Is Ollama running?")


def main():
    print("VLM Provider Test Suite")
    print("="*50)
    
    # Show current configuration
    print("\nCurrent Configuration:")
    print(f"Provider: {config.get('vlm.provider', 'ollama')}")
    print(f"VLM Enabled: {config.get('vlm.enabled', False)}")
    
    # Test Ollama
    test_provider('ollama', 'llama3.2-vision')
    
    # List available Ollama models
    list_ollama_models()
    
    # Test OpenAI if API key is available
    if os.getenv('OPENAI_API_KEY') or config.get('vlm.openai_api_key'):
        test_provider('openai', 'gpt-4o')
    else:
        print("\n" + "="*50)
        print("OpenAI Testing Skipped")
        print("="*50)
        print("Set OPENAI_API_KEY environment variable to test OpenAI")
        print("Example: export OPENAI_API_KEY='your-api-key'")
    
    print("\n" + "="*50)
    print("Quick Setup Guide:")
    print("="*50)
    print("\n1. To use Ollama (free, local):")
    print("   - Install: curl -fsSL https://ollama.com/install.sh | sh")
    print("   - Start server: ollama serve")
    print("   - Pull model: ollama pull llama3.2-vision")
    print("   - Configure: uv run python -m snapmark.utils.vlm_config switch ollama llama3.2-vision")
    
    print("\n2. To use OpenAI (paid, cloud):")
    print("   - Get API key from: https://platform.openai.com/api-keys")
    print("   - Set key: export OPENAI_API_KEY='your-key'")
    print("   - Configure: uv run python -m snapmark.utils.vlm_config switch openai gpt-4o")
    
    print("\n3. Check status:")
    print("   - uv run python -m snapmark.utils.vlm_config status")


if __name__ == "__main__":
    main()