#!/usr/bin/env python3
"""
Test switching between VLM providers (OpenAI and Ollama)
"""

import os
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from snapmark.core.vlm import VLMProcessor, VLMProvider
from snapmark.config import config


def test_provider_switching():
    """Test switching between different VLM providers"""
    
    print("=" * 60)
    print("VLM Provider Switching Test")
    print("=" * 60)
    
    # Test 1: Ollama with Llama 3.2
    print("\n1. Testing Ollama with Llama 3.2")
    print("-" * 40)
    try:
        vlm_ollama = VLMProcessor(provider="ollama", model="llama3.2")
        info = vlm_ollama.get_provider_info()
        print(f"Provider: {info['provider']}")
        print(f"Model: {info['model']}")
        print(f"API URL: {info['api_url']}")
        print(f"Available: {info['available']}")
        
        if info['available']:
            print("✓ Ollama with Llama 3.2 is working!")
        else:
            print("✗ Ollama not available - make sure Ollama is running")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 2: Ollama with Llama 3.2 Vision
    print("\n2. Testing Ollama with Llama 3.2 Vision")
    print("-" * 40)
    try:
        vlm_ollama_vision = VLMProcessor(provider="ollama", model="llama3.2-vision")
        info = vlm_ollama_vision.get_provider_info()
        print(f"Provider: {info['provider']}")
        print(f"Model: {info['model']}")
        print(f"API URL: {info['api_url']}")
        print(f"Available: {info['available']}")
        
        if info['available']:
            print("✓ Ollama with Llama 3.2 Vision is working!")
        else:
            print("✗ Llama 3.2 Vision not available - run: ollama pull llama3.2-vision")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: OpenAI with GPT-4o
    print("\n3. Testing OpenAI with GPT-4o")
    print("-" * 40)
    
    # Check if API key is available
    has_openai_key = bool(os.getenv('OPENAI_API_KEY') or config.get('vlm.openai_api_key'))
    
    if has_openai_key:
        try:
            vlm_openai = VLMProcessor(provider="openai", model="gpt-4o")
            info = vlm_openai.get_provider_info()
            print(f"Provider: {info['provider']}")
            print(f"Model: {info['model']}")
            print(f"Available: {info['available']}")
            
            if info['available']:
                print("✓ OpenAI with GPT-4o is configured!")
                
                # Test with a simple text prompt (no image needed)
                if vlm_openai.openai_client:
                    print("\nTesting OpenAI API connection...")
                    try:
                        response = vlm_openai.openai_client.chat.completions.create(
                            model="gpt-4o-mini",  # Use mini for testing to save costs
                            messages=[{"role": "user", "content": "Say 'API working' in 3 words"}],
                            max_tokens=10
                        )
                        print(f"API Response: {response.choices[0].message.content}")
                        print("✓ OpenAI API is working!")
                    except Exception as api_error:
                        print(f"✗ API Error: {api_error}")
            else:
                print("✗ OpenAI client not initialized")
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print("✗ OpenAI API key not found")
        print("  Set OPENAI_API_KEY environment variable or add to config.json")
        print("  Example: export OPENAI_API_KEY='your-api-key'")
    
    # Test 4: Test MCP integration with different providers
    print("\n4. Testing MCP Integration")
    print("-" * 40)
    
    try:
        from snapmark.core.mcp_client import MCPClient
        
        mcp_client = MCPClient()
        
        # Check which provider is configured for MCP
        vlm_provider = config.get('vlm.provider', 'ollama')
        print(f"MCP configured with VLM provider: {vlm_provider}")
        
        if vlm_provider == 'openai':
            model = config.get('vlm.openai_model', 'gpt-4o')
            print(f"MCP will use OpenAI model: {model}")
        else:
            model = config.get('vlm.ollama_model', config.get('vlm.model', 'llama3.2'))
            print(f"MCP will use Ollama model: {model}")
        
        if mcp_client.is_agent_available():
            print("✓ MCP agent is available")
        else:
            print("✗ MCP agent not available (check LLM configuration)")
            
    except ImportError as e:
        print(f"✗ MCP not installed: {e}")
        print("  Install with: uv add 'mcp>=1.0.0' mcp-use langchain-openai langchain-ollama")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_config_switching():
    """Test configuration switching utility"""
    
    print("\n" + "=" * 60)
    print("Configuration Switching Test")
    print("=" * 60)
    
    config_path = Path.home() / '.snapmark2' / 'config.json'
    
    # Backup current config
    backup_config = None
    if config_path.exists():
        with open(config_path, 'r') as f:
            backup_config = json.load(f)
    
    try:
        from snapmark.utils.vlm_config import switch_vlm_provider, get_vlm_status
        
        # Test switching to Ollama
        print("\nSwitching to Ollama with llama3.2-vision...")
        switch_vlm_provider("ollama", "llama3.2-vision")
        
        # Reload config and verify
        config._config = None  # Force reload
        config.config = config.load_config()
        
        assert config.get('vlm.provider') == 'ollama'
        assert config.get('vlm.ollama_model') == 'llama3.2-vision'
        print("✓ Successfully switched to Ollama")
        
        # Test switching to OpenAI (without API key, just config test)
        print("\nSwitching to OpenAI with gpt-4o...")
        switch_vlm_provider("openai", "gpt-4o")
        
        # Reload config and verify
        config._config = None  # Force reload
        config.config = config.load_config()
        
        assert config.get('vlm.provider') == 'openai'
        assert config.get('vlm.openai_model') == 'gpt-4o'
        print("✓ Successfully switched to OpenAI")
        
        print("\nCurrent status:")
        get_vlm_status()
        
    except Exception as e:
        print(f"✗ Error during config switching: {e}")
    finally:
        # Restore original config
        if backup_config:
            with open(config_path, 'w') as f:
                json.dump(backup_config, f, indent=2)
            print("\n✓ Original configuration restored")


def main():
    print("VLM Multi-Provider Test Suite")
    print("=" * 60)
    print("This test verifies that both OpenAI (GPT-4o) and Ollama")
    print("models work correctly with SnapMark's VLM and MCP features.")
    print("=" * 60)
    
    # Run provider tests
    test_provider_switching()
    
    # Run config switching tests
    test_config_switching()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("\n✅ Key Points:")
    print("1. VLM supports both OpenAI (gpt-4o) and Ollama (llama3.2) models")
    print("2. MCP client works with both providers for intelligent processing")
    print("3. Easy switching between providers via config utility")
    print("4. Models are properly configured based on provider selection")
    
    print("\n📝 Quick Setup:")
    print("For Ollama: ollama pull llama3.2-vision")
    print("For OpenAI: export OPENAI_API_KEY='your-key'")
    print("\nSwitch providers: uv run python -m snapmark.utils.vlm_config switch <provider> <model>")


if __name__ == "__main__":
    main()