import os
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import io
from enum import Enum


class VLMProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai" 
    AZURE_OPENAI = "azure_openai"


class VLMProcessor:
    """Vision Language Model processor supporting multiple providers (Ollama, OpenAI, Azure OpenAI)"""
    
    def __init__(self, provider: str = None, api_url: str = None, model: str = None):
        # Import here to avoid circular imports
        from ..config import config
        
        self.provider = VLMProvider(provider or config.get('vlm.provider', 'ollama'))
        self.api_url = (api_url or config.get('vlm.api_url', 'http://localhost:11434')).rstrip('/')
        
        # Set model based on provider
        if self.provider == VLMProvider.OLLAMA:
            self.model = model or config.get('vlm.ollama_model', config.get('vlm.model', 'llama3.2-vision'))
        elif self.provider == VLMProvider.OPENAI:
            self.model = model or config.get('vlm.openai_model', 'gpt-4o')
        elif self.provider == VLMProvider.AZURE_OPENAI:
            self.model = model or config.get('vlm.azure_model', 'gpt-4-vision')
        else:
            self.model = model or config.get('vlm.model', 'llama3.2-vision')
        
        # Initialize clients based on provider
        self.openai_client = None
        self.azure_client = None
        
        if self.provider == VLMProvider.OPENAI:
            self._init_openai_client()
        elif self.provider == VLMProvider.AZURE_OPENAI:
            self._init_azure_client()
    
    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            from ..config import config
            
            api_key = config.get('vlm.openai_api_key') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or configure in vlm.openai_api_key")
            
            self.openai_client = OpenAI(api_key=api_key)
                
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: uv add openai")
    
    def _init_azure_client(self):
        """Initialize Azure OpenAI client"""
        try:
            from openai import AzureOpenAI
            from ..config import config
            
            api_key = config.get('vlm.azure_api_key') or os.getenv('AZURE_OPENAI_API_KEY')
            endpoint = config.get('vlm.azure_endpoint') or os.getenv('AZURE_OPENAI_ENDPOINT')
            api_version = config.get('vlm.azure_api_version', '2024-02-01')
            
            if not api_key or not endpoint:
                raise ValueError("Azure OpenAI API key and endpoint required. Set environment variables or configure in config")
            
            self.azure_client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version
            )
                
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: uv add openai")
        
    def encode_image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string for API call"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def describe_image(self, image_path: str, prompt: Optional[str] = None) -> str:
        """Generate description of image using VLM"""
        if not Path(image_path).exists():
            return f"Error: Image file not found at {image_path}"
        
        if not prompt:
            prompt = "Describe this image in detail. Focus on the main content, text if visible, interface elements, and any actionable information. Save the content into excel."
        
        try:
            if self.provider == VLMProvider.OLLAMA:
                return self._describe_image_ollama(image_path, prompt)
            elif self.provider == VLMProvider.OPENAI:
                return self._describe_image_openai(image_path, prompt)
            elif self.provider == VLMProvider.AZURE_OPENAI:
                return self._describe_image_azure(image_path, prompt)
            else:
                return f"Error: Unsupported VLM provider: {self.provider}"
                
        except Exception as e:
            return f"Error generating image description: {str(e)}"
    
    def _describe_image_ollama(self, image_path: str, prompt: str) -> str:
        """Generate description using Ollama"""
        try:
            # Encode image to base64
            base64_image = self.encode_image_to_base64(image_path)
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False
            }
            
            # Make API call to Ollama
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # Increased timeout for vision models
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No description generated")
            else:
                return f"API Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Ollama API. Make sure Ollama is running."
        except requests.exceptions.Timeout:
            return "Error: Request timed out. The model might be loading."
    
    def _describe_image_openai(self, image_path: str, prompt: str) -> str:
        """Generate description using OpenAI"""
        if not self.openai_client:
            return "Error: OpenAI client not initialized"
        
        try:
            # Encode image to base64
            base64_image = self.encode_image_to_base64(image_path)
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
    
    def _describe_image_azure(self, image_path: str, prompt: str) -> str:
        """Generate description using Azure OpenAI"""
        if not self.azure_client:
            return "Error: Azure OpenAI client not initialized"
        
        try:
            # Encode image to base64
            base64_image = self.encode_image_to_base64(image_path)
            
            response = self.azure_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Azure OpenAI API Error: {str(e)}"
    
    def extract_action_items_from_image(self, image_path: str) -> str:
        """Extract action items or tasks visible in the image"""
        prompt = """
        Look at this image and identify any tasks, action items, to-dos, or actionable information.
        Focus on:
        - Task lists or checkboxes
        - Calendar events or deadlines
        - Notes about things to do
        - Meeting action items
        - Any text that suggests actions to be taken
        
        Return the action items in a clear, bulleted format. If no action items are found, say "No action items detected in image."
        """
        
        return self.describe_image(image_path, prompt)
    
    def extract_key_information(self, image_path: str) -> str:
        """Extract key information and insights from the image"""
        prompt = """
        Analyze this image and extract the most important information. Focus on:
        - Key data, numbers, or metrics
        - Important names, dates, or locations
        - Main topics or themes
        - Critical information that someone might want to reference later
        
        Provide a concise summary of the key information found.
        """
        
        return self.describe_image(image_path, prompt)
    
    def is_available(self) -> bool:
        """Check if the VLM service is available"""
        try:
            if self.provider == VLMProvider.OLLAMA:
                response = requests.get(f"{self.api_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    tags = response.json()
                    models = [model["name"] for model in tags.get("models", [])]
                    # Check for exact match or with :latest tag
                    model_name = self.model
                    if model_name in models:
                        return True
                    # Check if model exists with :latest tag
                    if f"{model_name}:latest" in models:
                        # Update the model name to include the tag for API calls
                        self.model = f"{model_name}:latest"
                        return True
                    # Check if model without tag exists when we have a tag
                    if ":" in model_name:
                        base_model = model_name.split(":")[0]
                        if base_model in models:
                            return True
                    return False
                return False
            elif self.provider == VLMProvider.OPENAI:
                return self.openai_client is not None
            elif self.provider == VLMProvider.AZURE_OPENAI:
                return self.azure_client is not None
            return False
        except:
            return False
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider and model"""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "api_url": self.api_url if self.provider == VLMProvider.OLLAMA else None,
            "available": self.is_available()
        }
    
    @classmethod
    def list_available_models(cls, provider: str = "ollama", api_url: str = None) -> list:
        """List available models for a given provider"""
        if provider == "ollama":
            try:
                url = (api_url or "http://localhost:11434").rstrip('/')
                response = requests.get(f"{url}/api/tags", timeout=5)
                if response.status_code == 200:
                    tags = response.json()
                    return [model["name"] for model in tags.get("models", [])]
            except:
                pass
        elif provider == "openai":
            # Common OpenAI vision models
            return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision-preview"]
        return []