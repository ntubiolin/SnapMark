import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from .ai_chat import AIChat


class AISummaryGenerator:
    def __init__(self, api_key: Optional[str] = None):
        # Use AIChat for unified AI interface
        self.ai_chat = None
        
    def generate_custom_summary(self, notes: List[str], prompt: str, model: str = "gpt-4o-mini", days: int = 1) -> str:
        """Generate a custom summary based on user prompt"""
        if not notes:
            return "No notes found for summary generation."
            
        if not self.ai_chat:
            # Initialize with specified model
            provider = None
            if model.startswith(("gpt", "o1")):
                provider = "openai"
            elif model.startswith("claude"):
                provider = "claude"
            elif model.startswith("gemini"):
                provider = "gemini"
            else:
                provider = "ollama"
                
            self.ai_chat = AIChat(provider=provider, model=model)
            
        combined_content = "\n\n---\n\n".join(notes)
        
        full_prompt = f"""
{prompt}

以下是過去 {days} 天的截圖筆記內容：

{combined_content}
"""
        
        try:
            response = self.ai_chat.send_message(full_prompt)
            return response
        except Exception as e:
            return f"生成摘要時發生錯誤: {str(e)}"
            
    def generate_summary_with_prompt(self, notes: List[str], custom_prompt: str) -> str:
        """Generate summary with custom prompt - wrapper for generate_custom_summary"""
        return self.generate_custom_summary(notes, custom_prompt)
            
    def generate_daily_summary(self, notes: List[str], date: Optional[datetime] = None) -> str:
        if not notes:
            return "No notes found for summary generation."
        
        if not date:
            date = datetime.now()
        
        combined_content = "\n\n".join(notes)
        
        prompt = f"""
Please analyze the following screenshot notes from {date.strftime('%Y-%m-%d')} and create a concise summary:

{combined_content}

Please provide:
1. A brief overview of the main activities/topics captured
2. Key information or insights from the screenshots
3. Any patterns or recurring themes
4. Important action items or follow-ups mentioned

Keep the summary concise but informative, focusing on the most relevant content.
"""
        
        if not self.ai_chat:
            self.ai_chat = AIChat(provider="openai", model="gpt-3.5-turbo")
        
        try:
            response = self.ai_chat.send_message(prompt)
            return response
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def generate_note_summary(self, ocr_text: str, context: str = "") -> str:
        if not ocr_text.strip():
            return "No text content available for summary."
        
        prompt = f"""
Please summarize the following OCR text extracted from a screenshot:

OCR Text:
{ocr_text}

{f"Context: {context}" if context else ""}

Provide a brief, clear summary of the main points and any actionable information.
"""
        
        if not self.ai_chat:
            self.ai_chat = AIChat(provider="openai", model="gpt-3.5-turbo")
        
        try:
            response = self.ai_chat.send_message(prompt)
            return response
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def extract_action_items(self, text_content: str) -> List[str]:
        prompt = f"""
Extract any action items, tasks, or to-dos from the following text:

{text_content}

Return only the action items as a simple list, one item per line. If no action items are found, return "No action items found."
"""
        
        if not self.ai_chat:
            self.ai_chat = AIChat(provider="openai", model="gpt-3.5-turbo")
        
        try:
            response = self.ai_chat.send_message(prompt)
            
            if "No action items found" in response:
                return []
            
            return [item.strip().lstrip('- ') for item in response.split('\n') if item.strip()]
        except Exception as e:
            return [f"Error extracting action items: {str(e)}"]