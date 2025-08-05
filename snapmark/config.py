import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    def __init__(self, config_file: str = None):
        self.config_file = config_file or str(Path.home() / '.snapmark2' / 'config.json')
        self.config_dir = Path(self.config_file).parent
        self.config_dir.mkdir(exist_ok=True)
        
        self.defaults = {
            "output_directory": "SnapMarkData",
            "ocr_language": "eng+chi_tra+chi_sim",
            "hotkeys": {
                "screenshot": "cmd+shift+3",
                "window_screenshot": "cmd+shift+4"
            },
            "ai_summary": {
                "enabled": False,
                "daily_time": "18:00",
                "weekly_day": "sunday",
                "weekly_time": "19:00"
            },
            "vlm": {
                "enabled": False,
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
                "enabled": False,
                "config_path": "config/mcp_use_config.json",
                "timeout": 120.0,
                "default_prompt": "Analyze this screenshot and extract any relevant data into an Excel workbook with appropriate worksheets and formatting.",
                "servers": {
                    "excel": {
                        "enabled": False,
                        "command": "uvx",
                        "args": ["excel-mcp-server", "stdio"],
                        "env": {
                            "EXCEL_FILES_PATH": "./SnapMarkData/exports"
                        }
                    }
                }
            },
            "gui": {
                "system_tray": True,
                "minimize_to_tray": True,
                "startup_minimized": False
            },
            "storage": {
                "image_quality": 85,
                "auto_cleanup_days": 0  # 0 = disabled
            }
        }
        
        self.config = self.load_config()
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override values taking precedence."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                # Deep merge with defaults
                config = self._deep_merge(self.defaults, user_config)
                return config
            except (json.JSONDecodeError, IOError):
                pass
        
        # Save defaults if config doesn't exist
        self.save_config(self.defaults)
        return self.defaults.copy()
    
    def save_config(self, config: Dict[str, Any] = None):
        config = config or self.config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Failed to save config: {e}")
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value):
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_output_dir(self) -> str:
        return os.path.expanduser(self.get("output_directory", "SnapMarkData"))
    
    def get_openai_key(self) -> str:
        return os.getenv('OPENAI_API_KEY', '')


# Alias for backwards compatibility
ConfigManager = Config

# Global config instance
config = Config()