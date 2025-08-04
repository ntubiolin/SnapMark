import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import openai


class AISummaryGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY')
        )
        
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
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes screenshot notes and OCR content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
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
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes OCR text from screenshots."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def extract_action_items(self, text_content: str) -> List[str]:
        prompt = f"""
Extract any action items, tasks, or to-dos from the following text:

{text_content}

Return only the action items as a simple list, one item per line. If no action items are found, return "No action items found."
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that identifies action items and tasks from text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            result = response.choices[0].message.content.strip()
            if "No action items found" in result:
                return []
            
            return [item.strip().lstrip('- ') for item in result.split('\n') if item.strip()]
        except Exception as e:
            return [f"Error extracting action items: {str(e)}"]