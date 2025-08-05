import os
from typing import List, Dict, Any, Optional
from enum import Enum
import base64
from pathlib import Path

class AIProvider(Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OLLAMA = "ollama"

class AIChat:
    """Unified AI chat interface supporting multiple providers"""
    
    def __init__(self, provider: str = None, model: str = None):
        from ..config import config
        
        # Determine provider based on model name if not explicitly provided
        if not provider and model:
            if model.startswith(("gpt", "o1")):
                provider = "openai"
            elif model.startswith("claude"):
                provider = "claude"
            elif model.startswith("gemini"):
                provider = "gemini"
            else:
                provider = config.get("ai_chat.default_provider", "openai")
        
        self.provider = AIProvider(provider or config.get("ai_chat.default_provider", "openai"))
        self.model = model
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize client based on provider
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """Initialize the appropriate AI client"""
        from ..config import config
        
        if self.provider == AIProvider.OPENAI:
            try:
                from openai import OpenAI
                # Check ai_chat key first, then fallback to vlm key, then environment
                api_key = (config.get("ai_chat.openai_api_key") or 
                          config.get("vlm.openai_api_key") or 
                          os.getenv("OPENAI_API_KEY"))
                if not api_key:
                    # For demo purposes, use a dummy client that shows helpful error messages
                    raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add 'vlm.openai_api_key' to ~/.snapmark2/config.json")
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed")
                
        elif self.provider == AIProvider.AZURE_OPENAI:
            try:
                from openai import AzureOpenAI
                # Check ai_chat keys first, then fallback to vlm keys, then environment
                api_key = (config.get("ai_chat.azure_api_key") or 
                          config.get("vlm.azure_api_key") or 
                          os.getenv("AZURE_OPENAI_API_KEY"))
                endpoint = (config.get("ai_chat.azure_endpoint") or 
                           config.get("vlm.azure_endpoint") or 
                           os.getenv("AZURE_OPENAI_ENDPOINT"))
                if not api_key or not endpoint:
                    raise ValueError("Azure OpenAI credentials not found")
                self.client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=endpoint,
                    api_version=config.get("ai_chat.azure_api_version", config.get("vlm.azure_api_version", "2024-02-01"))
                )
            except ImportError:
                raise ImportError("OpenAI package not installed")
                
        elif self.provider == AIProvider.CLAUDE:
            try:
                import anthropic
                api_key = config.get("ai_chat.claude_api_key") or os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("Claude API key not found")
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed")
                
        elif self.provider == AIProvider.GEMINI:
            try:
                import google.generativeai as genai
                api_key = config.get("ai_chat.gemini_api_key") or os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("Gemini API key not found")
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.model or 'gemini-1.5-pro')
            except ImportError:
                raise ImportError("Google GenerativeAI package not installed")
                
        elif self.provider == AIProvider.OLLAMA:
            # Ollama uses HTTP API, no special client needed
            self.api_url = config.get("ai_chat.ollama_api_url", "http://localhost:11434")
            
    def send_message(self, message: str, image_path: Optional[str] = None) -> str:
        """Send a message to the AI and get a response"""
        try:
            # Add user message to history
            user_msg = {"role": "user", "content": message}
            if image_path:
                user_msg["image_path"] = image_path
            self.conversation_history.append(user_msg)
            
            # Get response based on provider
            if self.provider == AIProvider.OPENAI:
                response = self._send_openai(message, image_path)
            elif self.provider == AIProvider.AZURE_OPENAI:
                response = self._send_azure(message, image_path)
            elif self.provider == AIProvider.CLAUDE:
                response = self._send_claude(message, image_path)
            elif self.provider == AIProvider.GEMINI:
                response = self._send_gemini(message, image_path)
            elif self.provider == AIProvider.OLLAMA:
                response = self._send_ollama(message, image_path)
            else:
                response = f"Provider {self.provider} not implemented"
                
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"
            
    def _send_openai(self, message: str, image_path: Optional[str] = None) -> str:
        """Send message to OpenAI"""
        messages = self._prepare_openai_messages(message, image_path)
        
        response = self.client.chat.completions.create(
            model=self.model or "gpt-4o-mini",
            messages=messages,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    def _send_azure(self, message: str, image_path: Optional[str] = None) -> str:
        """Send message to Azure OpenAI"""
        messages = self._prepare_openai_messages(message, image_path)
        
        response = self.client.chat.completions.create(
            model=self.model or "gpt-4",
            messages=messages,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    def _send_claude(self, message: str, image_path: Optional[str] = None) -> str:
        """Send message to Claude"""
        messages = []
        
        # Convert history to Claude format
        for msg in self.conversation_history[:-1]:  # Exclude the last user message we just added
            if msg["role"] == "user":
                content = msg["content"]
                if "image_path" in msg and Path(msg["image_path"]).exists():
                    # Claude expects base64 images
                    with open(msg["image_path"], "rb") as f:
                        image_data = base64.b64encode(f.read()).decode()
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": content},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data
                                }
                            }
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "assistant", "content": msg["content"]})
                
        # Add current message
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data
                        }
                    }
                ]
            })
        else:
            messages.append({"role": "user", "content": message})
            
        response = self.client.messages.create(
            model=self.model or "claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=2000
        )
        
        return response.content[0].text
        
    def _send_gemini(self, message: str, image_path: Optional[str] = None) -> str:
        """Send message to Gemini"""
        from PIL import Image
        
        parts = [message]
        
        if image_path and Path(image_path).exists():
            image = Image.open(image_path)
            parts.append(image)
            
        response = self.client.generate_content(parts)
        return response.text
        
    def _send_ollama(self, message: str, image_path: Optional[str] = None) -> str:
        """Send message to Ollama"""
        import requests
        
        payload = {
            "model": self.model or "llama2",
            "prompt": message,
            "stream": False
        }
        
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            payload["images"] = [image_data]
            
        response = requests.post(
            f"{self.api_url}/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("response", "No response")
        else:
            return f"Ollama error: {response.status_code}"
            
    def _prepare_openai_messages(self, message: str, image_path: Optional[str] = None) -> List[Dict]:
        """Prepare messages for OpenAI/Azure format"""
        messages = []
        
        # Add conversation history
        for msg in self.conversation_history[:-1]:  # Exclude the last user message
            if msg["role"] == "user":
                content = msg["content"]
                if "image_path" in msg and Path(msg["image_path"]).exists():
                    with open(msg["image_path"], "rb") as f:
                        image_data = base64.b64encode(f.read()).decode()
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": content},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "assistant", "content": msg["content"]})
                
        # Add current message
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            })
        else:
            messages.append({"role": "user", "content": message})
            
        return messages
        
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history.copy()


class AIChatProcessor:
    """Async wrapper for AI chat to work with Streamlit"""
    
    def __init__(self, provider: str = None, model: str = None):
        try:
            self.ai_chat = AIChat(provider, model)
            self.initialized = True
        except Exception as e:
            self.ai_chat = None
            self.initialized = False
            self.error = str(e)
        
    async def process_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Process message with context (async for Streamlit compatibility)"""
        if not self.initialized:
            return f"AI chat initialization failed: {getattr(self, 'error', 'Unknown error')}"
        
        # Extract image path from context if available
        image_path = context.get('image_path') if context else None
        
        # Add context information to the message if available
        if context:
            enhanced_message = message
            if context.get('ocr_text'):
                enhanced_message += f"\n\nOCR Text from image: {context['ocr_text']}"
            if context.get('vlm_description'):
                enhanced_message += f"\n\nImage description: {context['vlm_description']}"
        else:
            enhanced_message = message
            
        # Use the synchronous AI chat in a way that works with async
        response = self.ai_chat.send_message(enhanced_message, image_path)
        return response
        
    def clear_history(self):
        """Clear conversation history"""
        if self.initialized:
            self.ai_chat.clear_history()
        
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        if self.initialized:
            return self.ai_chat.get_history()
        return []